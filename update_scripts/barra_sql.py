import os
import json
import glob
import logbook

logger = logbook.Logger('barra')

from zipfile import ZipFile
from ftplib import FTP

server, usr, pwd = 'ftp.barra.com', 'knaphlbp', 'manlqtnx'
ftpdir = 'bime'

idfile = 'SMD_CNE5_X_ID_%s.zip'
Dfile1 = 'SMD_CNE5D_100_%s.zip'
Dfile2 = 'SMD_CNE5D_100_UnadjCov_%s.zip'
Sfile1 = 'SMD_CNE5S_100_%s.zip'
Sfile2 = 'SMD_CNE5S_100_UnadjCov_%s.zip'

zipdir = '/home/SambaServer/extend_data/Barra/src'
dirdir = '/home/SambaServer/extend_data/Barra'

def fetch_files(date):
    ftp = FTP(server, usr, pwd)
    logger.info('FTP server connected')
    ftp.cwd(ftpdir)
    _files = []
    ftp.retrlines("LIST", _files.append)
    files = []
    for _file in _files:
        _file = _file.strip().split()[-1]
        if _file.find(date[2:8]) != -1:
            files.append(_file)
            logger.info('Found file {}', _file)
    _idfile = idfile % date[2:8]
    if _idfile not in files:
        logger.warning('{} not found', _idfile)
    for file in map(lambda x: x % date[2:8], [Dfile1, Dfile2, Sfile1, Sfile2]):
        if file not in files:
            logger.warning('{} not found', file)

    zips = set()
    for file in files:
        try:
            zip = os.path.join(zipdir, file)
            with open(zip, 'w') as fh:
                ftp.retrbinary("RETR " + file, fh.write)
            logger.info('{} fetched and stored as {}', file, zip)
        except:
            logger.error('Failed to fetch file {}', file)
        zips.add(zip)
    return zips

def unzip_files(date, zips):
    _idfile = os.path.join(zipdir, idfile % date[2:8])
    if _idfile in zips:
        zips.discard(_idfile)
        zipfile = ZipFile(_idfile)
        zipfile.extract('CHN_X_Asset_ID.%s' % date, dirdir)
        for oldfile in glob.glob(os.path.join(dirdir, 'CHN_X_Asset_ID*')):
            os.remove(oldfile)
            logger.debug('Removed file {}', oldfile)
    while zips:
        zipf = zips.pop()
        model = 'daily' if zipf.find('CNE5D') != -1 else 'short'
        dstdir = os.path.join(dirdir, model, date[:4], date[4:6], date[6:8])
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
            logger.debug('Created directory {}', dstdir)
        zipfile = ZipFile(zipf)
        logger.info('Extracting files from {}:\n{}', zipf, '\n\t'.join(zipfile.namelist()))
        zipfile.extractall(dstdir)

def get_idmaps(date):
    idmaps = {}
    _idfile = sorted(glob.glob(os.path.join(dirdir, 'CHN_X_Asset_ID*')))[-1]
    with open(_idfile) as file:
        for line in file:
            try:
                bid, marker, sid, start, end = [item.strip() for item in line.split('|')]
                assert marker == 'LOCALID'
                sid = sid[2:8]
                if date <= end:
                    idmaps[bid] = sid
            except:
                pass
    return idmaps

def get_exposure(date, model, idmaps):
    dstdir = os.path.join(dirdir, model, date[:4], date[4:6], date[6:8])
    expfile = 'CNE5' + model[0].upper() + '_100_Asset_Exposure.%s' % date
    expfile = os.path.join(dstdir, expfile)

    res = {}
    with open(expfile) as file:
        for line in file:
            try:
                bid, fac, exp, _ = [item.strip() for item in line.split('|')]
                exp = float(exp)
                if fac not in res:
                    res[fac] = {}
                res[fac][idmaps[bid]] = exp
            except:
                pass
    return expfile, res

def fetch_and_parse(date):
    zips = fetch_files(date)
    unzip_files(date, zips)
    idmaps = get_idmaps(date)
    dstdir = os.path.join(dirdir, '%s', date[:4], date[4:6], date[6:8])
    try:
        with open(os.path.join(dstdir % 'daily', 'idmaps.%s.json' % date), 'w') as dfile:
            json.dump(idmaps, dfile)
    except:
        pass
    try:
        expfile, expjson = get_exposure(date, 'daily', idmaps)
        with open(expfile+'.json', 'w') as file:
            json.dump(expjson, file)
    except:
        pass
    try:
        with open(os.path.join(dstdir % 'short', 'idmaps.%s.json' % date), 'w') as sfile:
            json.dump(idmaps, sfile)
    except:
        pass
    try:
        expfile, expjson = get_exposure(date, 'short', idmaps)
        with open(expfile+'.json', 'w') as file:
            json.dump(expjson, file)
    except:
        pass


"""
some file path utilities
"""

def gp_dir(date, model):
    return os.path.join(dirdir, model, date[:4], date[4:6], date[6:8])

def gp_idfile(date):
    return os.path.join(dirdir, 'CHN_X_Asset_ID.' + date)

def gp_idmaps(date, model):
    return os.path.join(gp_dir(date, model), 'idmaps.%s.json' % date)

def gp_expjson(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5'+model[0].upper()+'_100_Asset_Exposure.%s.json' % date)

def gp_facret(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5'+model[0].upper()+'_100_DlyFacRet.%s' % date)

def gp_faccov(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5'+model[0].upper()+'_100_Covariance.%s' % date)

def gp_precov(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5'+model[0].upper()+'_100_preVRACovariance.%s' % date)

def gp_specret(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5_100_Asset_DlySpecRet.%s' % date)

def gp_specs(date, model):
    return os.path.join(gp_dir(date, model), 'CNE5'+model[0].upper()+'_100_Asset_Data.%s' % date)
