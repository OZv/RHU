#!/usr/bin/env python
# -*- coding: utf-8 -*-
## rhu_downloader.py
## A helpful tool to fetch data from website & generate mdx source file
##
## This program is a free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, version 3 of the License.
##
## You can get a copy of GNU General Public License along this program
## But you can always get it from http://www.gnu.org/licenses/gpl.txt
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
import os
import re
import random
import string
import urllib
import fileinput
import requests
from os import path
from datetime import datetime
from multiprocessing import Pool
from collections import OrderedDict


MAX_PROCESS = 25
STEP = 25000
F_WORDLIST = 'wordlist.txt'


def fullpath(file, suffix='', base_dir=''):
    if base_dir:
        return ''.join([os.getcwd(), path.sep, base_dir, file, suffix])
    else:
        return ''.join([os.getcwd(), path.sep, file, suffix])


def readdata(file, base_dir=''):
    fp = fullpath(file, base_dir=base_dir)
    if not path.exists(fp):
        print("%s was not found under the same dir of this tool." % file)
    else:
        fr = open(fp, 'rU')
        try:
            return fr.read()
        finally:
            fr.close()
    return None


def dump(data, file, mod='w'):
    fname = fullpath(file)
    fw = open(fname, mod)
    try:
        fw.write(data)
    finally:
        fw.close()


def removefile(file):
    if path.exists(file):
        os.remove(file)


def info(l, s='word'):
    return '%d %ss' % (l, s) if l>1 else '%d %s' % (l, s)


def randomstr(digit):
    return ''.join(random.sample(string.ascii_lowercase, 1)+
        random.sample(string.ascii_lowercase+string.digits, digit-1))


def getpage(link, BASE_URL=''):
    r = requests.get(''.join([BASE_URL, link]), timeout=10, allow_redirects=False)
    if r.status_code == 200:
        return r.content
    else:
        return None


def getwordlist(file, base_dir='', tolower=False):
    words = readdata(file, base_dir)
    if words:
        wordlist = []
        p = re.compile(r'\s*\n\s*')
        words = p.sub('\n', words).strip()
        for word in words.split('\n'):
            w, u = word.split('\t')
            if tolower:
                wordlist.append((w.strip().lower(), u.strip().lower()))
            else:
                wordlist.append((w, u))
        return wordlist
    print("%s: No such file or file content is empty." % file)
    return []


class downloader:
#common logic
    def __init__(self, name):
        self.__session = None
        self.DIC_T = name

    @property
    def session(self):
        return self.__session

    def login(self, ORIGIN='', REF=''):
        HEADER = 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.102 Safari/537.36'
        self.__session = requests.Session()
        self.__session.headers['User-Agent'] = HEADER
        self.__session.headers['Origin'] = ORIGIN
        self.__session.headers['Referer'] = REF

    def logout(self):
        pass

    def makeurl(self, cur):
        pass

    def getcref(self, url, raiseErr=True):
        pass

    def makeword(self, page, word, words, logs, d_app):
        pass

    def formatEntry(self, key, line, crefs, links, logs):
        pass

    def getpage(self, link, BASE_URL=''):
        r = self.__session.get(''.join([BASE_URL, link]), timeout=10, allow_redirects=False)
        if r.status_code == 200:
            return (r.status_code, r.content)
        elif r.status_code == 301:
            return (r.status_code, r.headers['Location'])
        else:
            return (r.status_code, None)

    def cleansp(self, html):
        p = re.compile(r'\s+')
        html = p.sub(' ', html)
        p = re.compile(r'<!--[^<>]+?-->')
        html = p.sub('', html)
        p = re.compile(r'\s*<br/?>\s*')
        html = p.sub('<br>', html)
        p = re.compile(r'(\s*<br>\s*)*(<hr[^>]*>)(\s*<br>\s*)*', re.I)
        html = p.sub(r'\2', html)
        p = re.compile(r'(\s*<br>\s*)*(<(?:/?(?:div|p)[^>]*|br)>)(\s*<br>\s*)*', re.I)
        html = p.sub(r'\2', html)
        p = re.compile(r'\s*(<(?:/?(?:div|p|ul|li)[^>]*|br)>)\s*', re.I)
        html = p.sub(r'\1', html)
        p = re.compile(r'\s+(?=[,\.;\?\!])')
        html = p.sub(r'', html)
        p = re.compile(r'\s+(?=</?\w+>[\)\]\s])')
        html = p.sub(r'', html)
        return html

    def getcreflist(self, file, base_dir=''):
        words = readdata(file, base_dir)
        if words:
            p = re.compile(r'\s*\n\s*')
            words = p.sub('\n', words).strip()
            crefs = {}
            for word in words.split('\n'):
                k, v = word.split('\t')
                crefs[urllib.unquote(k).strip().lower()] = v.strip()
                crefs[v.strip().lower()] = v.strip()
            return crefs
        print("%s: No such file or file content is empty." % file)
        return {}

    def __mod(self, flag):
        return 'a' if flag else 'w'

    def __dumpwords(self, sdir, words, sfx='', finished=True):
        f = fullpath('rawhtml.txt', sfx, sdir)
        if len(words):
            mod = self.__mod(sfx)
            fw = open(f, mod)
            try:
                [fw.write('\n'.join([en[0], en[1], '</>\n'])) for en in words]
            finally:
                fw.close()
        elif not path.exists(f):
            fw = open(f, 'w')
            fw.write('\n')
            fw.close()
        if sfx and finished:
            removefile(fullpath('failed.txt', '', sdir))
            l = -len(sfx)
            cmd = '\1'
            nf = f[:l]
            if path.exists(nf):
                msg = "Found rawhtml.txt in the same dir, delete?(default=y/n)"
                cmd = 'y'#raw_input(msg)
            if cmd == 'n':
                return
            elif cmd != '\1':
                removefile(nf)
            os.rename(f, nf)

    def is_uni_word(self, key, ref, links):
        uni = False
        ps = re.compile(r'[\s\-\'/]|\.$')
        uc = ps.sub(r'', key).lower()
        if uc != ps.sub(r'', ref):
            if not ref in links:
                links[ref] = [key]
                uni = True
            else:
                uni = True
                for c in links[ref]:
                    if uc == ps.sub(r'', c).lower():
                        uni = False
                        break
                if uni:
                    links[ref].append(key)
        return uni

    def __fetchdata_and_make_mdx(self, arg, part, suffix=''):
        sdir, d_app = arg['dir'], OrderedDict()
        words, logs, crefs, count, failed, links = [], [], OrderedDict(), 1, [], {}
        leni = len(part)
        ps = re.compile(r'[\s\-\'/]|\.$')
        while leni:
            for cur, url in part:
                if count % 100 == 0:
                    print ".",
                    if count % 1000 == 0:
                        print count,
                try:
                    status, page = self.getpage(self.makeurl(url.replace('/', '%2f')))
                    if page:
                        if status == 200:
                            if self.makeword(page, cur, words, logs, d_app):
                                url = urllib.unquote(url).strip().lower()
                                crefs[url] = cur
                                count += 1
                        else:
                            ref = self.getcref(urllib.unquote(page), False)
                            if ref:
                                ref = ref.strip().lower()
                                if self.is_uni_word(cur, ref, links):
                                    words.append([cur, ''.join(['@@@LINK=', ref])])
                                    count += 1
                    elif status != 404:
                        print "%s failed, retry automatically later" % cur
                        failed.append((cur, url))
                    else:
                        logs.append("I01: cannot find '%s', ignore" % cur)
                except Exception, e:
                    import traceback
                    print traceback.print_exc()
                    print "%s failed, retry automatically later" % cur
                    failed.append((cur, url))
            lenr = len(failed)
            if lenr >= leni:
                break
            else:
                leni = lenr
                part, failed = failed, []
        print "%s browsed" % info(count-1),
        if crefs:
            mod = self.__mod(path.exists(fullpath('cref.txt', base_dir=sdir)))
            dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in crefs.iteritems()]), '\n']), ''.join([sdir, 'cref.txt']), mod)
        if d_app:
            mod = self.__mod(path.exists(fullpath('appd.txt', base_dir=sdir)))
            dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in d_app.iteritems()]), '\n']), ''.join([sdir, 'appd.txt']), mod)
        if failed:
            dump(''.join(['\n'.join(['\t'.join([w, u]) for w, u in failed]), '\n']), ''.join([sdir, 'failed.txt']))
            self.__dumpwords(sdir, words, '.part', False)
        else:
            print ", 0 word failed"
            self.__dumpwords(sdir, words, suffix)
        if logs:
            mod = self.__mod(path.exists(fullpath('log.txt', base_dir=sdir)))
            dump('\n'.join(logs), ''.join([sdir, 'log.txt']), mod)
        return d_app

    def start(self, arg):
        import socket
        socket.setdefaulttimeout(120)
        import sys
        reload(sys)
        sys.setdefaultencoding('utf-8')
        sdir = arg['dir']
        fp1 = fullpath('rawhtml.txt.part', base_dir=sdir)
        fp2 = fullpath('failed.txt', base_dir=sdir)
        fp3 = fullpath('rawhtml.txt', base_dir=sdir)
        if path.exists(fp1) and path.exists(fp2):
            print ("Continue last failed")
            failed = getwordlist('failed.txt', sdir)
            return self.__fetchdata_and_make_mdx(arg, failed, '.part')
        elif not path.exists(fp3):
            print ("New session started")
            return self.__fetchdata_and_make_mdx(arg, arg['alp'])

    def combinefiles(self, dir):
        print "combining files..."
        times = 0
        imgpath = fullpath('p', path.sep)
        if not path.exists(imgpath):
            os.mkdir(imgpath)
        for d in os.listdir(fullpath(dir)):
            if path.isdir(fullpath(''.join([dir, d, path.sep]))):
                times += 1
        for fn in ['cref.txt', 'log.txt']:
            fw = open(fullpath(''.join([dir, fn])), 'w')
            for i in xrange(1, times+1):
                sdir = ''.join([dir, '%d'%i, path.sep])
                if path.exists(fullpath(fn, base_dir=sdir)):
                    fw.write('\n'.join([readdata(fn, sdir).strip(), '']))
            fw.close()
        words, logs = [], []
        crefs = self.getcreflist('cref.txt', dir)
        fw = open(fullpath(''.join([dir, self.DIC_T, path.extsep, 'txt'])), 'w')
        d_uni, links = {}, {}
        try:
            for i in xrange(1, times+1):
                sdir = ''.join([dir, '%d'%i, path.sep])
                file = fullpath('rawhtml.txt', base_dir=sdir)
                lns = []
                for ln in fileinput.input(file):
                    ln = ln.strip()
                    if ln == '</>':
                        ukey = lns[0].lower().strip()
                        if not ukey in d_uni:
                            entry = self.formatEntry(lns[0], lns[1], crefs, links, logs)
                            if entry:
                                fw.write(''.join([entry, '\n']))
                                d_uni[ukey] = None
                                words.append(lns[0])
                        del lns[:]
                    elif ln:
                        lns.append(ln)
        finally:
            fw.close()
        print "%s totally" % info(len(words))
        fw = open(fullpath(''.join([dir, 'words.txt'])), 'w')
        fw.write('\n'.join(words))
        fw.close()
        if logs:
            mod = self.__mod(path.exists(fullpath('log.txt', base_dir=dir)))
            dump('\n'.join(logs), ''.join([dir, 'log.txt']), mod)


def f_start((obj, arg)):
    return obj.start(arg)


def multiprocess_fetcher(d_refs, wordlist, obj, base):
    times = int(len(wordlist)/STEP)
    pl = [wordlist[i*STEP: (i+1)*STEP] for i in xrange(0, times)]
    pl.append(wordlist[times*STEP:])
    times = len(pl)
    dir = fullpath(obj.DIC_T)
    if not path.exists(dir):
        os.mkdir(dir)
    for i in xrange(1, times+1):
        subdir = ''.join([obj.DIC_T, path.sep, '%d'%(base+i)])
        subpath = fullpath(subdir)
        if not path.exists(subpath):
            os.mkdir(subpath)
    pool = Pool(MAX_PROCESS)
    d_app = OrderedDict()
    leni = times+1
    while 1:
        args = []
        for i in xrange(1, times+1):
            sdir = ''.join([obj.DIC_T, path.sep, '%d'%(base+i), path.sep])
            file = fullpath(sdir, 'rawhtml.txt')
            if not(path.exists(file) and os.stat(file).st_size):
                param = {}
                param['alp'] = pl[i-1]
                param['dir'] = sdir
                args.append((obj, param))
        lenr = len(args)
        if len(args) > 0:
            if lenr >= leni:
                print "The following parts cann't be fully downloaded:"
                for arg in args:
                    print arg[1]['dir']
                break
            else:
                dts = pool.map(f_start, args)#f_start(args[0])#for debug
                [d_app.update(dict) for dict in dts]
        else:
            break
        leni = lenr
    dt = OrderedDict()
    for k, v in d_app.iteritems():
        if not k in d_refs:
            dt[k] = v
    return times, dt.items()


def getlink(ap, dict):
    p1 = re.compile(r'<li\s+class="result_list"><a\s+href="([^<>"]+)"', re.I)
    for la in p1.findall(ap):
        lp = getpage(la)
        p2 = re.compile(r'<li\s+class="result_list"><a\s+href="http://dictionary\.reference\.com/browse/([^<>"]+)"[^<>]*>(.+?)</a>', re.I)
        for url, word in p2.findall(lp):
            dict[word] = url.replace('+', ' ')


def getalphadict(a):
    dict = OrderedDict()
    ap = getpage(a)
    while ap:
        getlink(ap, dict)
        n = re.compile(r'<a class="lnkactive" href="/([^<>"]+)">NEXT', re.I)
        m = n.search(ap)
        ap = getpage(m.group(1), 'http://dictionary.reference.com/') if m else None
    return dict


def makewordlist(file):
    fp = fullpath(file)
    if path.exists(fp):
        return OrderedDict(getwordlist(file))
    else:
        print "Get word list: start at %s" % datetime.now()
        page = getpage('http://dictionary.reference.com/')
        p = re.compile(r'<a\s+href="(http://dictionary\.reference\.com/list/\w)">\w</a>', re.I)
        pool = Pool(10)
        alphadicts = pool.map(getalphadict, [a for a in p.findall(page)])
        dt = OrderedDict()
        [dt.update(dict) for dict in alphadicts]
        dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in dt.iteritems()]), '\n']), file)
        print "%s totally" % info(len(dt))
        print "Get word list: finished at %s" % datetime.now()
        return dt


def is_complete(path, ext='.part'):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(ext):
                return False
    return True


class dic_downloader(downloader):
#RHU downloader
    def __init__(self):
        downloader.__init__(self, 'RHU')
        self.__base_url = 'http://dictionary.reference.com/browse/'

    def makeurl(self, cur):
        return ''.join([self.__base_url, cur])

    def getcref(self, url, raiseErr=True):
        p = re.compile(''.join([self.__base_url, r'(.+)(?=$)']), re.I)
        m = p.search(url)
        if not m and raiseErr:
            raise AssertionError('%s : Wrong URL'%url)
        return m.group(1) if m else None

    def __cmpkt(self, k, t):
        rst = t.find(k)>-1 or k.find(t)>-1
        if not rst:
            p = re.compile(r'[ \-]')
            t, k = p.sub(r'', t), p.sub(r'', k)
            rst = t.find(k)>-1 or k.find(t)>-1
        return rst

    def __get_text(self, tag):
        p = re.compile(r'</?[^<>]+>')
        return p.sub(r'', tag)

    def __preformat(self, page):
        p = re.compile(r'[\n\r]+')
        page = p.sub(r'', page)
        p = re.compile(r'[\t]+|&nbsp;')
        page = p.sub(r' ', page)
        p = re.compile(r'<!--[^<>]+?-->')
        page = p.sub(r'', page)
        p = re.compile(r'<span\s+class="oneClick-link(?:\s+oneClick-available)?">([^<>]*?)</span>', re.I)
        page = p.sub(r'\1', page)
        p = re.compile(r'(<div\s+class=[\'"]sent-wrap [^<>]*>)', re.I)
        page = p.sub(r'', page)
        p = re.compile(r'(</?)strong(?=[^>]*>)')
        page = p.sub(r'\1b', page)
        return page

    def __rec_url(self, div, d_app):
        p = re.compile(r'<a\s+href="http://dictionary\.reference\.com/browse/([^<>"]+)">\s*(.+?)\s*</a>', re.I)
        for url, word in p.findall(div):
            url = urllib.unquote(url).strip().lower()
            if not url in d_app:
                d_app[url] = word

    def makeword(self, page, word, words, logs, d_app):
        exist = False
        page = self.__preformat(page)
        p = re.compile(r'<div\s+class="nearby-words-inner-box"[^<>]*>.+?</div>', re.I)
        m = p.search(page)
        if not m:
            print "'%s' has no Nearby words" % word
            logs.append("W01:'%s' has no Nearby words" % word)
        else:
            self.__rec_url(m.group(0), d_app)
        p = re.compile(r'<section[^<>]*\bid="source-luna"', re.I)
        if not p.search(page):
            logs.append("I02: '%s' is not found in DIC" % word)
        else:
            p = re.compile('<h1\s+class="head-entry">(.+?)</h1>', re.I)
            m = p.search(page)
            if not m:
                raise AssertionError('E01:%s has no title' % word)
            ttl = self.__get_text(m.group(1))
            if not self.__cmpkt(word.strip().lower(), ttl.strip().lower()):
                logs.append("W02: '%s' vs '%s'\t:key is not equal to title" % (word, ttl))
            p = re.compile(r'(<section\s+id="source-luna"[^<>]*>.+?)\s*<div\s+class="source-meta">\s*Dictionary\.com\s+Unabridged.+?</div>\s*(</section>)', re.I)
            m1 = p.search(page)
            p = re.compile(r'<section\s+class="related-words-box"[^<>]*>.+?</section>', re.I)
            mr = p.search(page)
            rlt = mr.group(0) if mr else ''
            p = re.compile(r'<section\s+id="source-example-sentences"[^<>]*>.+?</section>', re.I)
            mx = p.search(page)
            exm = mx.group(0) if mx else ''
            p = re.compile(r'<section\s+id="difficulty-box"[^<>]*>.+?</section>', re.I)
            md = p.search(page)
            difc = md.group(0)if md else ''
            worddef = ''.join([m1.group(1), m1.group(2), rlt, exm, difc])
            worddef = self.cleansp(worddef).strip()
            words.append([word, worddef])
            exist = True
        return exist

    def __repaud(self, m):
        text = m.group(1)
        p = re.compile(r'href="http://static\.sfdict\.com/staticrep/dictaudio/([^"]+?)\.mp3"', re.I)
        m = p.search(text)
        return ''.join(['<img src="vc.png" onclick="asr(this, \'', m.group(1), '\')" class="mip">'])

    def __tslink(self, m):
        cls = 'n9x' if m.group(1)=='roman' else 'jpx'
        return ''.join([cls, m.group(2), 'entry://', m.group(3).replace('/', '%2F')])

    def __tslink2(self, m):
        return ''.join(['entry://', m.group(1).replace('/', '%2F')])

    def __repanc(self, m, idl):
        id = randomstr(4)
        idl[m.group(2)] = id
        return ''.join([m.group(1), m.group(3), '<a id="', id, '"></a>'])

    def __repimg(self, m):
        file = ''.join(['p/', m.group(3)])
        if not path.exists(fullpath(file)):
            dump(self.getpage(''.join([m.group(2), m.group(3)]))[1], file, 'wb')
        return ''.join(['"iva" ', m.group(1), '"', file, '"'])

    def __rephdr(self, m, idl):
        text = m.group(1)
        p = re.compile(r'<li><a data-href="([^<>"]+)">\s*([^<>]+?)\s*</a></li>', re.I)
        ll = []
        for id, str in p.findall(text):
            if id in idl:
                ll.append(''.join(['<a href="entry://#', idl[id], '">', str, '</a> ']))
        return ''.join(ll)

    def __fmtdef(self, m):
        dc = m.group(2)
        p = re.compile(r'((?:[^\w\s]|^)\s*<span class=")dbox-italic(">[A-Z][\w\s\-\,\.\/]+?\w)([\,\.]\s*</span>|</span>[\,\.])')
        dc = p.sub(r'\1zjt\2\3', dc)
        p = re.compile(r'(?<=<span class=")zjt(?=">[^<>]+?[A-Z]\.\s*</span>\s*\w)')
        dc = p.sub(r'eet', dc)
        p = re.compile(r'\(\s*(<span class=")dbox-italic"[^<>]*>([\w\s]*used with[\w\s]*)(</span>)\s*\)', re.I)
        dc = p.sub(r'\1wy7">(\2)\3', dc)
        return self.__fmtdef2(''.join([m.group(1), dc]))

    def __fmtdef2(self, dc):
        p = re.compile(r'(<span class="dbox-(?:bold|sc|italic)"[^<>]*>)(.+?)(,\s*)(</span>)', re.I)
        return p.sub(r'\1\2\4\3', dc)

    def __fmttail(self, m):
        lbl = m.group(1)
        if lbl.find('tail-type-origin')>-1:
            return m.group(0)
        else:
            p = re.compile(r'(<div class="tail-header\s*[^<>]+>)(.+)(?=</div>)', re.I)
            th = p.sub(r'\1<span class="nwz">\2</span><img src="ac.png" class="gjy" onclick="ytu(this)">', m.group(2))
            return ''.join([m.group(1), th])

    def __fmttelm(self, m):
        elm = m.group(1)
        if elm.find('<br>')>-1:
            elm = ''.join(['<p>', elm.replace('<br>', '</p><p>'), '</p>'])
        return elm

    def __fmtexphd(self, m):
        dif = m.group(1)
        ul = m.group(4)
        if dif!='Contemporary' or ul.count('</li>')>5:
            sty = ' style="display:none"'
            img = 'ax'
        else:
            sty = ''
            img = 'ac'
        return ''.join(['<span class="nwz">', dif, m.group(2),
        '</span><img src="', img, '.png" class="gjy" onclick="ytu(this)">', m.group(3), sty, ul])

    def __fmtcred(self, m):
        p = re.compile(r'<a href[^<>]+>\s*(.*?)\s*</a>', re.I)
        cred = p.sub(r'\1', m.group(2))
        p = re.compile(r'<span>\s*(.+?)\s*</span>\s*<span>\s*(.+?)\s*</span>\s*<span class="oneClick-disabled">\s*(\w{3})\w*(\s.+?)\s*</span>', re.I)
        cred = p.sub(r'<span>\2, </span><i>\1</i> <span>(\3\4)</span>', cred)
        p = re.compile(r'<span>\s*(.+?)\s*</span>\s*<span class="oneClick-disabled">\s*(.+?)\s*</span>', re.I)
        cred = p.sub(r'<span>\2, </span><i>\1</i>', cred)
        p = re.compile(r'<i>([^<>]{30})([^<>]+)</i>', re.I)
        cred = p.sub(r'<i title="\1\2">\1</i>...', cred)
        return ''.join([m.group(1), cred])

    def __repcls(self, m):
        tag = m.group(1)
        cls = m.group(3)
        self.span = {'me': 'snr', 'pron spellpron': 'seu', 'dbox-bold': 'eds',
        'pron ipapron': 'kyi', 'dbox-pg': 'f1v', 'def-number': 'lno',
        'dbox-roman': 'rdg', 'dbox-italic': 'eet', 'dbox-example': 'cie',
        'dbox-sc': 'mcy', 'dbus_altslash': 'iuf', 'dbox-romann': 'wuu',
        'def-block-label': 'zsc', 'dbox-hn': 'unb', 'pre-def-data': 'uzu',
        'dbus_persn': 'oda', 'dbus_pron_sup': 'pc6', 'dbus_ford': 'joq',
        'dbus_langc': 'fx6', 'def-block-label-synonyms': 'x8g', 'pronset': 'w2p',
        'def-block-label-antonyms': 'q6s', 'tail-source-info': 'gsu',
        'dbus_author_ed': 'eed', 'dbox-italic dbox-bold': 'n7z'}
        self.div = {'source-box oneClick-area': 'c4d', 'waypoint-wrapper header-row header-first-row': 'y2u',
        'header-row header-extras pronounce pronset': 'k0a', 'header-row': 'lxv',
        'source-data': 'z5o', 'def-list': 'vy5', 'def-set': 'uy4', 'def-content': 'u72',
        'tail-wrapper': 'r1q', 'tail-box tail-type-origin pm-btn-spot': 'tw0',
        'tail-header waypoint-wrapper': 'kwy', 'tail-content': 'tsj', 'tail-elements': 'tqa',
        'source-title': 'tlh', 'source-subtitle oneClick-disabled': 'yns',
        'partner-example-credentials': 'qxr', 'def-block def-inline-example': 'lld',
        'tail-header': 'tgi', 'tail-content ce-spot': 'nwt',
        'header-row header-first-row': 'uh3', 'tail-box tail-type-relf pm-btn-spot': 'hlb',
        'tail-box tail-type-synonyms pm-btn-spot': 'r6w', 'tail-box tail-type-antonyms pm-btn-spot': 'bl7',
        'def-block': 'ebf', 'tail-box tail-type-var pm-btn-spot': 'thm',
        'tail-box tail-type-varf pm-btn-spot': 'tno', 'tail-box tail-type-ref pm-btn-spot': 'rof',
        'tail-box tail-type-usage_note pm-btn-spot': 'vs7', 'tail-box tail-type-conf pm-btn-spot': 'cwg',
        'tail-box tail-type-regional_vars pm-btn-spot': 'ey7', 'tail-box tail-type-grammar_note pm-btn-spot': 'ywk',
        'tail-box tail-type-word_story pm-btn-spot': 'zhq', 'tail-box tail-type-pronunciation_note pm-btn-spot': 'pj4',
        'tail-box tail-type-synstudy pm-btn-spot': 'sdd', 'tail-box tail-type-popular_references pm-btn-spot': 'par',
        'tail-box tail-type-cites pm-btn-spot': 'ne7', 'ts normal': 'sgt', 'ts boldface': 'rbw',
        'usage-alert': 'uau', 'tail-box tail-type-confusables_note pm-btn-spot': 'w2z',
        'ts lightface': 'ymr', 'content': 'nwt'}
        self.hd = {'main-header oneClick-disabled head-big': 'hq2', 'luna-data-header': 'kly',
        'main-header oneClick-disabled head-medium': 'oi9', 'main-header oneClick-disabled head-small': 'sqy',
        'usage-alert-header': 'una'}
        self.sec = {'luna-box': 'yik', 'def-pbk ce-spot': 'nq3', 'usage-alert-block ce-spot': 'uju',
        'source-wrapper source-example-sentences is-pm-btn-show pm-btn-spot': 'e7f',
        'related-words-box': 'bcr'}
        self.h3 = {'head-entry-variants': 'aws', 'title': 'x7r'}
        self.li = {'size-1': 'jk5', 'size-2': 'p3q', 'size-3': 'pz3', 'size-4': 'y4a'}
        if tag=='div' and cls in self.div:
            return ''.join([tag, m.group(2), self.div[cls]])
        elif tag=='span' and cls in self.span:
            return ''.join([tag, m.group(2), self.span[cls]])
        elif tag=='section' and cls in self.sec:
            return ''.join([tag, m.group(2), self.sec[cls]])
        elif tag=='header' and cls in self.hd:
            return ''.join([tag, m.group(2), self.hd[cls]])
        elif tag=='h3' and cls in self.h3:
            return ''.join([tag, m.group(2), self.h3[cls]])
        elif tag=='li' and cls in self.li:
            return ''.join([tag, m.group(2), self.li[cls]])
        elif tag=='p' and cls=='partner-example-text':
            return ''.join([tag, m.group(2), 'p7c'])
        elif tag=='h1' and cls=='head-entry':
            return ''.join([tag, m.group(2), 'bih'])
        elif tag=='h2' and cls=='head-entry':
            return ''.join([tag, m.group(2), 'qih'])
        elif tag=='ol' and cls=='def-sub-list':
            return ''.join([tag, m.group(2), 'ocy'])
        elif tag=='ul' and cls=='list-vertical':
            return ''.join([tag, m.group(2), 'utg'])
        else:
            return m.group(0)

    def __repprn(self, m):
        prn = m.group(1)
        return prn.replace('"eds"', '"b7a"').replace('"mcy"', '"mfe"').replace('"eet"', '"ity"')

    def formatEntry(self, key, line, crefs, links, logs):
        if line.startswith('@@@'):
            lk, ref = line.split('=')
            if ref in crefs:
                p = re.compile(r'[\s\-\'/]|\.$')
                if p.sub(r'', key).lower()!=p.sub(r'', crefs[ref]).lower() and self.is_uni_word(key, ref, links):
                    return '\n'.join([key, ''.join(['@@@LINK=', crefs[ref].replace('/', '%2F')]), '</>'])
                else:
                    return ''
            else:
                logs.append("E02: The ref target of '%s' is not found" % key)
                return ''
        n = 1
        while n:
            p = re.compile(r'(?<=data-syllable=")([^<>"]*?)<[^<>]+>[^<>"]*?</[^<>"]+>', re.I)
            line, n = p.subn(r'\1', line)
        line = line.replace('&lt;span class="', '<span class="')
        p = re.compile(r'(data-syllable="[^<>"]+")&gt;', re.I)
        line = p.sub(r'\1>', line)
        n = 1
        while n:
            p = re.compile(r'<(?=[^<>]*</?\w+\b)', re.I)
            line, n = p.subn(r'&lt;', line)
        n = 1
        while n:
            p = re.compile(r'(<[^<>]+>[^<>]*)>', re.I)
            line, n = p.subn(r'\1&gt;', line)
        p = re.compile(r'(?<=<section)[^<>]*\bid="source-luna"[^<>]*(?=>)', re.I)
        line = p.sub(r' class="ti9"', line)
        p = re.compile(r'data-syllable="([^<>"]+)">[^<>]+(?=</span>)', re.I)
        line = p.sub(r'>\1', line)
        p = re.compile(r'<div class="audio-wrapper">(.+?)</div>', re.I)
        line = p.sub(self.__repaud, line)
        p = re.compile(r'(</h[12]>)(<img src="vc.png"[^<>]+>)', re.I)
        line = p.sub(r'\2\1', line)
        p = re.compile(r'<button\s+class="(?:prontoggle|syllable-button)[^<>]+>[^<>]*?</button>', re.I)
        line = p.sub(r'', line)
        p = re.compile('<button[^<>]+>\s*Expand\s*</button>', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'<div class="map-origin">.+?</div>(?=<div class="timeline oneClick-disabled">|&lt;|[^<>]*(?:<a\s|<span class="(?:dbox-roman|dbus_ford|dbox-italic|dbus_persn)">))', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'<div class="timeline oneClick-disabled"><div class="span"[^<>]*>.+?</div></div>', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'<div class="source-meta">.+?</div>', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'(?<=<a class=")dbox-xref dbox-(roman|bold)(" href=")http://dictionary\.reference\.com/browse/([^<>"]+)(?=">)', re.I)
        line = p.sub(self.__tslink, line)
        p = re.compile(r'(?<=<a href=")http://dictionary\.reference\.com/browse/([^<>"]+)(?=">)', re.I)
        line = p.sub(self.__tslink2, line)
        p = re.compile(r'<a\s+href="http://www\.thesaurus\.com/browse/[^<>"]+">(.+?)</a>', re.I)
        line = p.sub(r'\1', line)
        p = re.compile(r'(?<=<img class=)[^<>]+?(src=)[\'"](http://static\.sfdict\.com/dictstatic/dictionary/graphics/luna/)([^<>/\'"]+)[^<>]+(?=>)', re.I)
        line = p.sub(self.__repimg, line)
        p = re.compile(r'<section\s+id="difficulty-box"\s+data-difficulty="(\d+)".+?<span class="subtext">([^<>]+)</span>\s*</section>', re.I)
        m = p.search(line)
        if m:
            dcbox = ''.join(['<div class="wf6"><img src="idc.png" class="i4g" title="', m.group(2), '"><img src="ix.png" class="iho" alt="', m.group(1), '"></div>'])
            q = re.compile(r'(<header class="main-header oneClick-disabled head-(?:big|medium|small)">)', re.I)
            line = q.sub(''.join([r'\1', dcbox]), line, 1)
        line = p.sub('', line)
        p = re.compile(r'(<a href="http://[^<>"]+")(?=>)', re.I)
        line = p.sub(r'\1 target="_blank"', line)
        p = re.compile(r'(\s*[,\.]\s*)(</a>)', re.I)
        line = p.sub(r'\2\1', line)
        p = re.compile(r'(<div[^<>]+>Origin).+?(?=</div>)', re.I)
        line = p.sub(r'\1', line)
        n = 1
        while n:
            p = re.compile(r'<(\w+)[^<>]*>\s*</\1>', re.I)
            line, n = p.subn(r'', line)
        p = re.compile(r'(<span class="dbox-pg">[^<>]+</span>[^<>]*)\((<span class=")dbox-italic(">)([^<>]+)(</span>)\)', re.I)
        line = p.sub(r'\1\2wtq\3(\4)\5', line)
        p = re.compile(r'(\xC2\xB7)')
        line = p.sub(r'<span></span>', line)
        p = re.compile(r'(<div class="def-content">)(.+?)(?=</div>)', re.I)
        line = p.sub(self.__fmtdef, line)
        p = re.compile(r'(<div[^<>]+><ol class=")def-sub-list(?=">)', re.I)
        line = p.sub(r'\1ozp', line)
        p = re.compile(r'(<ol class="def-sub-list">)(.+?)(?=</ol>)', re.I)
        line = p.sub(self.__fmtdef, line)
        p = re.compile(r'(?<=<div class="tail-elements">)(.+?)(?=</div>)', re.I)
        line = p.sub(lambda m: self.__fmtdef2(m.group(1)), line)
        p = re.compile(r'(<div class="tail-box tail-type-[^<>"\s]+? pm-btn-spot"[^<>]*>)(.+?</div>)', re.I)
        line = p.sub(self.__fmttail, line)
        p = re.compile(r'(?<=div class="tail-elements">)(.+?)(?=</div>)', re.I)
        line = p.sub(self.__fmttelm, line)
        p = re.compile(r'<header>\s*(<h3 class="title">)(Related Words?)(</h3>)\s*</header>', re.I)
        line = p.sub(r'\1<span class="ach">\2</span><img src="ac.png" class="gjy" onclick="ytu(this)">\3', line)
        p = re.compile(r'(<(?:div|section)[^<>]*?)\bid="([^<>"]+)"([^<>]*>)', re.I)
        idl = {}
        line = p.sub(lambda m: self.__repanc(m, idl), line)
        p = re.compile(r'(?<=<div class="header-row">)(.+?)(?=</div>)', re.I)
        line = p.sub(lambda m: self.__rephdr(m, idl), line)
        n = 1
        while n:
            p = re.compile(r'(<\w+[^<>]+?)\s*data-[\-\w]+=(?:"[^<>"]*"|\'[^<>\']*\')', re.I)
            line, n = p.subn(r'\1', line)
        p = re.compile(r'(?<=</span>)\s*\(<span[^<>]+>Show IPA</span>\)', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'\s*(</span>)\s*(?=<span class="pron ipapron">)', re.I)
        line = p.sub(r' \1 ', line)
        p = re.compile(r'(?<=<span class="def-number">)(\d+)\.(?=</span>)', re.I)
        line = p.sub(r'\1 ', line)
        p = re.compile(r'(<span class="dbox-pg">[^<>]+?)([\,\.]\s*)(</span>)', re.I)
        line = p.sub(r'\1\3\2', line)
        p = re.compile(r'(?<=<span class="dbox-pg">)([^<>\(\)]+)(\([^<>\(\)]+\))', re.I)
        line = p.sub(r'\1<span class="wy7">\2</span>', line)
        p = re.compile(r'<div class="source-title">Examples from the Web for.+?</div>', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'(?<=<div class="source-subtitle oneClick-disabled">)(\w+?)(\sExamples)(</div><ul)(>.+?)(?=</ul>)', re.I)
        line = p.sub(self.__fmtexphd, line)
        p = re.compile(r'(<div class="partner-example-credentials"[^<>]*>)(.+?)(?=</div>)', re.I)
        line = p.sub(self.__fmtcred, line)
        p = re.compile(r'(?<=<)(span|div|header|section|h[1-3]|p|ol|li|ul)\s*(\sclass=")([^<>"]+?)\s*(?=")', re.I)
        line = p.sub(self.__repcls, line)
        p = re.compile(r'(</?)(?:header|section)(?=[^>]*>)', re.I)
        line = p.sub(r'\1div', line)
        p = re.compile(r'\s+(?=>|</?div|</?p)', re.I)
        line = p.sub(r'', line)
        p = re.compile(r'(?<=<span class="seu">)(.+?)(?=<span class="kyi">)', re.I)
        line = p.sub(self.__repprn, line)
        p = re.compile(r'(?<=<span class=")(?:ity|eet)(">[^<>]+)(</span>)(\s*[\,\.])', re.I)
        line = p.sub(r'eet\1\3\2', line)
        p = re.compile(r'(?<=<span class=")ity(?=">[^<>]+?\,\s*</span>)', re.I)
        line = p.sub(r'eet', line)
        src = ''.join(['<script type="text/javascript"src="r5.js"></script><script>if(typeof(w2z)=="undefined"){var _l=document.getElementsByTagName("link");var _r=/',
        self.DIC_T, '.css$/;for(var i=_l.length-1;i>=0;i--)with(_l[i].href){var _m=match(_r);if(_m&&_l[i].id=="khl"){document.write(\'<script src="\'+replace(_r,"r5.js")+\'"type="text/javascript"><\/script>\');break;}}}</script>'])
        line = ''.join(['<link id="khl"rel="stylesheet"href="', self.DIC_T, '.css"type="text/css"><div class="khr">', line, src, '</div>'])
        line = '\n'.join([key, line, '</>'])
        return line


if __name__=="__main__":
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", nargs="?", help="[p] To download missing words")
    parser.add_argument("file", nargs="?", help="[file name] To specify additional wordlist")
    print "Start at %s" % datetime.now()
    dic_dl = dic_downloader()
    dic_dl.login()
    if dic_dl.session:
        d_all = makewordlist(F_WORDLIST)
        d_refs = OrderedDict()
        for k, v in d_all.iteritems():
            d_refs[urllib.unquote(v).strip().lower()] = k
        args = parser.parse_args()
        dir = ''.join([dic_dl.DIC_T, path.sep])
        if args.patch == 'p':
            print "Start to download missing words..."
            dt, wordlist, base = OrderedDict(), [], 0
            for d in os.listdir(fullpath(dir)):
                if path.isdir(fullpath(''.join([dir, d, path.sep]))):
                    base += 1
            for i in xrange(1, base+1):
                sdir = ''.join([dir, '%d'%i, path.sep])
                if path.exists(fullpath('appd.txt', base_dir=sdir)):
                    dt.update(getwordlist(''.join([sdir, 'appd.txt'])))
            if args.file and path.isfile(fullpath(args.file)):
                for k, v in getwordlist(args.file):
                    dt[urllib.unquote(v).strip().lower()] = k
            for k, v in dt.iteritems():
                uk = urllib.unquote(k).strip().lower()
                if not uk in d_refs:
                    wordlist.append((v, k))
                    d_refs[uk] = v
        else:
            wordlist, base = d_all.items(), 0
        while wordlist:
            blks, addlist = multiprocess_fetcher(d_refs, wordlist, dic_dl, base)
            base += blks
            wordlist = []
            for k, v in addlist:
                wordlist.append((v, k))
            if addlist:
                print "Downloading additional words..."
                d_refs.update(addlist)
        dump(''.join(['\n'.join(['\t'.join([v, k]) for k, v in d_refs.iteritems()]), '\n']), F_WORDLIST)
        if is_complete(fullpath(dir)):
            dic_dl.combinefiles(dir)
        print "Done!"
        dic_dl.logout()
    else:
        print "ERROR: Login failed."
    print "Finished at %s" % datetime.now()
