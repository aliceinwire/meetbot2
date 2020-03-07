from . import writers

class _BaseItem(object):
    itemtype = None
    starthtml = ''
    endhtml = ''
    startrst = ''
    endrst = ''
    starttext = ''
    endtext = ''
    startmw = ''
    endmw = ''

    def get_replacements(self, M, escapewith):
        replacements = { }
        for name in dir(self):
            if name[0] == "_": continue
            replacements[name] = getattr(self, name)
        replacements['nick'] = escapewith(replacements['nick'])
        replacements['link'] = self.logURL(M)
        for key in ('line', 'prefix', 'suffix', 'topic'):
            if key in replacements:
                replacements[key] = escapewith(replacements[key])
        if 'url' in replacements:
            replacements['url_quoteescaped'] = \
                                      escapewith(self.url.replace('"', "%22"))

        return replacements

    def template(self, M, escapewith):
        template = { }
        for k,v in list(self.get_replacements(M, escapewith).items()):
            if k not in ('itemtype', 'line', 'topic',
                         'url', 'url_quoteescaped',
                         'nick', 'time', 'link', 'anchor'):
                continue
            template[k] = v
        return template

    def makeRSTref(self, M):
        if self.nick[-1] == '_':
            rstref = rstref_orig = "%s%s"%(self.nick, self.time)
        else:
            rstref = rstref_orig = "%s-%s"%(self.nick, self.time)
        count = 0
        while rstref in M.rst_refs:
            rstref = rstref_orig + inbase(count)
            count += 1
        link = self.logURL(M)
        M.rst_urls.append(".. _%s: %s"%(rstref, link+"#"+self.anchor))
        M.rst_refs[rstref] = True
        return rstref

    @property
    def anchor(self):
        return 'l-'+str(self.linenum)

    def logURL(self, M):
        return M.config.basename+'.log.html'


class Topic(_BaseItem):
    itemtype = 'TOPIC'
    html_template = """<tr><td><a href='%(link)s#%(anchor)s'>%(time)s</a></td>
        <th colspan=3>%(starthtml)sTopic: %(topic)s%(endhtml)s</th>
        </tr>"""
    #html2_template = ("""<b>%(starthtml)s%(topic)s%(endhtml)s</b> """
    #                  """(%(nick)s, <a href='%(link)s#%(anchor)s'>%(time)s</a>)""")
    html2_template = ("""%(starthtml)s%(topic)s%(endhtml)s """
                      """<span class="details">"""
                      """(<a href='%(link)s#%(anchor)s'>%(nick)s</a>, """
                      """%(time)s)"""
                      """</span>""")
    rst_template = """%(startrst)s%(topic)s%(endrst)s  (%(rstref)s_)"""
    text_template = """%(starttext)s%(topic)s%(endtext)s  (%(nick)s, %(time)s)"""
    mw_template = """%(startmw)s%(topic)s%(endmw)s  (%(nick)s, %(time)s)"""
    startrst = '**'
    endrst = '**'
    startmw = "'''"
    endmw = "'''"
    starthtml = '<b class="TOPIC">'
    endhtml = '</b>'

    def __init__(self, nick, line, linenum, time_):
        self.nick = nick ; self.topic = line ; self.linenum = linenum
        self.time = time.strftime("%H:%M:%S", time_)

    def _htmlrepl(self, M):
        repl = self.get_replacements(M, escapewith=writers.html)
        repl['link'] = self.logURL(M)
        return repl

    def html(self, M):
        return self.html_template%self._htmlrepl(M)

    def html2(self, M):
        return self.html2_template%self._htmlrepl(M)

    def rst(self, M):
        self.rstref = self.makeRSTref(M)
        repl = self.get_replacements(M, escapewith=writers.rst)
        if repl['topic']=='': repl['topic']=' '
        repl['link'] = self.logURL(M)
        return self.rst_template%repl

    def text(self, M):
        repl = self.get_replacements(M, escapewith=writers.text)
        repl['link'] = self.logURL(M)
        return self.text_template%repl

    def mw(self, M):
        repl = self.get_replacements(M, escapewith=writers.mw)
        return self.mw_template%repl

    def __str__(self):
        return "#topic %s" % self.topic