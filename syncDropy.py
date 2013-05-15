#!/usr/bin/env python
import time
from dropbox import client, rest, session
from configobj import ConfigObj
import os, sys

class syncDropy:
    """syncDropy interface"""
    config = None
    session = None
    client = None
    email = None
    textmail = ''
    smtpUser = None
    smtpPass = None
    smtpHost = None
    smtpPort = None
    smtpTLS = None

    def __init__(self):
        self.config = ConfigObj(os.path.dirname(os.path.realpath(__file__)) + '/syncDropy.conf')
        self.session = session.DropboxSession('zg0lwralmd71gum', 'j22yvqwp1mev83o', 'app_folder')

        try:
            TOKEN_KEY = self.config['SESSION']['TOKEN_KEY']
        except:
            TOKEN_KEY = None;

        try:
            TOKEN_SECRET = self.config['SESSION']['TOKEN_SECRET']
        except:
            TOKEN_SECRET = None;

        try:
            SMTP = self.config['SMTP']
        except:
            self.config['SMTP'] = {}
            self.config['SMTP']['USERNAME'] = ''
            self.config['SMTP']['PASSWORD'] = ''
            self.config['SMTP']['HOST'] = 'aspmx.l.google.com'
            self.config['SMTP']['PORT'] = '25'
            self.config['SMTP']['TLS'] = 'NO'
            self.config.write()
            print 'Edita el fichero syncDropy.conf y configura adecuadamente el servidor SMTP'

        try:
            self.smtpUser = self.config['SMTP']['USERNAME']
        except:
            self.smtpUser = None;

        try:
            self.smtpPass = self.config['SMTP']['PASSWORD']
        except:
            self.smtpPass = None;

        try:
            self.smtpHost = self.config['SMTP']['HOST']
        except:
            self.smtpHost = None;

        try:
            self.smtpPort = self.config['SMTP']['PORT']
        except:
            self.smtpPort = None;

        try:
            self.smtpTLS = self.config['SMTP']['TLS']
        except:
            self.smtpTLS = None;

        if not TOKEN_KEY or not TOKEN_SECRET:
            request_token = self.session.obtain_request_token()
            url = self.session.build_authorize_url(request_token)
            print u"URL: ", url
            print "Visita la URL y AUTORIZA la aplicacion, cuando lo haga pulse ENTER."
            raw_input()
            access_token = self.session.obtain_access_token(request_token)
            self.config['SESSION'] = {};
            self.config['SESSION']['TOKEN_KEY'] = access_token.key
            self.config['SESSION']['TOKEN_SECRET'] = access_token.secret
            self.config.write()
            TOKEN_KEY = access_token.key
            TOKEN_SECRET = access_token.secret
            
        self.session.set_token(TOKEN_KEY, TOKEN_SECRET)    
        self.client = client.DropboxClient(self.session)

        ainfo = self.client.account_info()
        self.email = ainfo['email']
        print u"Conectado a Dropbox: %s" % (ainfo['email'])
        
    def putfile(self, name, path='.'):
        pf = self.client.put_file(name, open(path + '/' + name), 1)
        pfname = pf['path']
        pfsize = pf['size']
        return (pfname, self.client.share(pfname)['url'], pfsize)

    def putfilechunked(self, name, path='.'):
        size = os.stat(path + '/' + name).st_size
        f = open(path + '/' + name, 'rb')

        uploader = self.client.get_chunked_uploader(f, size)
        while uploader.offset < size:
            try:
                upload = uploader.upload_chunked()
            except rest.ErrorResponse, e:
                time.sleep(1)
        try:
            pf = uploader.finish(name, 1)
            pfname = pf['path']
            pfsize = pf['size']
            return (pfname, self.client.share(pfname)['url'], pfsize)
        except rest.ErrorResponse, e:
            return (name, 'OMITIDO', 0)

    def proccesspath(self, syncpath='.', path='.'):
        from os import listdir
        from os.path import isfile

        abspath = syncpath + '/' + path

        l = listdir(abspath)
        for f in l:
            if isfile(abspath + '/' + f):
                if f[0] != '.':
                    name, url, size = self.putfilechunked(path + '/' + f, syncpath)
                    txt = u"Fichero: %s (%s) URL: %s" % (name, size, url)
                    self.textmail += txt + '\n'
                    print txt.encode('utf-8')
                os.remove(abspath + '/' + f)
            else:
                self.proccesspath(syncpath, path + '/' + f)
                os.rmdir(abspath + '/' + f)

    def is_locked(self, filepath):
        locked = None
        file_object = None
        if os.path.exists(filepath):
            try:
                buffer_size = 8
                file_object = open(filepath, 'a', buffer_size)
                if file_object:
                    locked = False
            except IOError, message:
                locked = True
            finally:
                if file_object:
                    file_object.close()
        return locked

    def sendmail(self, TO, FROM, SUBJECT, text):
        from smtplib import SMTP
        import string
 
        BODY = string.join((
            "From: %s" % FROM,
            "To: %s" % TO,
            "Subject: %s" % SUBJECT ,
            "",
            text
            ), "\r\n")

        mailServer = SMTP()
        mailServer.set_debuglevel(0)
        mailServer.connect(self.smtpHost,self.smtpPort)
        mailServer.ehlo()
        if self.smtpTLS == 'YES':
            mailServer.starttls()
        if self.smtpUser and self.smtpPass:
            mailServer.login(self.smtpUser,self.smtpPass)

        mailServer.sendmail(FROM, [TO], BODY.encode('utf-8'))
        mailServer.quit()

    def run(self, path='.'):
        from os.path import isfile

        while True:
            if isfile(path + '/ok'):
                os.remove(path + '/ok')
                print 'Proceso iniciado'
                self.textmail = ''
                self.proccesspath(path)
                if not self.textmail == '':
                    print 'Enviando Report por email a %s...' % (self.email)
                    self.sendmail(self.email, self.email, 'Report syncDropy', self.textmail)
                    print 'OK'
                print 'Fin de buble'
            time.sleep(10)
                
if len(sys.argv) >= 2:
    if not os.path.exists(sys.argv[1]):
        sys.stderr.write('ERROR: Directorio %s no existe!\n' % (sys.argv[1]))
        sys.exit(1)
    else:
        ruta = sys.argv[1]
else:
    ruta = '.'

d = syncDropy()
d.run(ruta)

