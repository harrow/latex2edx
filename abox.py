#!/usr/bin/python
#
# Answer Box class
#
# object representation of abox, used in Tutor2, now generalized to latex and word input formats.
# 13-Aug-12 ichaung: merge in sari's changes
# 13-Aug-12 ichuang: cleaned up, does more error checking, includes stub for shortanswer
#                    note that shortanswer can be implemented right now using customresponse and textbox
# 04-Sep-12 ichuang: switch from shlex to FSM, merge in changes for math and inline from 8.21
# 13-Oct-12 ichuang: remove csv entirely, use FSM for splitting options instead

import os, sys, string ,re
#import shlex	# for split keeping quoted strings intact
#import csv	# for splitting quoted options

from lxml import etree

class AnswerBox(object):
    def __init__(self,aboxstr):
        '''
        Parse a TUT abox and produce edX XML for a problem responsetype.

        Examples:
        -----------------------------------------------------------------------------
        <abox type="option" expect="float" options=" ","noneType","int","float" />
        
        <optionresponse>
        <optioninput options="('noneType','int','float')"  correct="int">
        </optionresponse>
        
        -----------------------------------------------------------------------------
        <abox type="string" expect="Michigan" options="ci" />
        
        <stringresponse answer="Michigan" type="ci">
        <textline size="20" />
        </stringresponse>
        
        -----------------------------------------------------------------------------
        <abox type="custom" expect="(3 * 5) / (2 + 3)" cfn="eq" />
        
        <customresponse cfn="eq">
        <textline size="40" correct_answer="(3 * 5) / (2 + 3)"/><br/>
        </customresponse>
        
        -----------------------------------------------------------------------------
        <abox type="numerical" expect="3.141" tolerance="5%" />
        
        <numericalresponse answer="5.0">
        <responseparam type="tolerance" default="5%" name="tol" description="Numerical Tolerance" />
        <textline />
        </numericalresponse>
        
        -----------------------------------------------------------------------------
	<abox type="multichoice" expect="Yellow" options="Red","Green","Yellow","Blue" />

        <multiplechoiceresponse direction="vertical" randomize="yes">
         <choicegroup type="MultipleChoice">
            <choice location="random" correct="false" name="red">Red</choice>
            <choice location="random" correct="true" name="green">Green</choice>
            <choice location="random" correct="false" name="yellow">Yellow</choice>
            <choice location="bottom" correct="false" name="blue">Blue</choice>
         </choicegroup>
        </multiplechoiceresponse>
        -----------------------------------------------------------------------------
        '''
        self.aboxstr = aboxstr
        self.xml = self.abox2xml(aboxstr)
        self.xmlstr = etree.tostring(self.xml)
        
    def abox2xml(self,aboxstr):
        if aboxstr.startswith('abox '): aboxstr = aboxstr[5:]
        s = aboxstr
        s = s.replace(' in_check= ',' ')

        # parse answer box arguments into dict
        abargs = self.abox_args(s)
        self.abargs = abargs

        type2response = { 'custom': 'customresponse',
                          'external': 'externalresponse',
                          'code': 'coderesponse',
                          'multichoice': 'multiplechoiceresponse',
                          'numerical': 'numericalresponse',
                          'option': 'optionresponse',
                          'shortans' : 'shortanswerresponse',
                          'shortanswer' : 'shortanswerresponse',
                          'string': 'stringresponse',
                          'symbolic': 'symbolicresponse',
                          }

        if 'type' in abargs and abargs['type'] in type2response:
            abtype = type2response[abargs['type']]
        elif 'tests' in abargs:
            abtype = 'externalresponse'
        elif 'type' not in abargs and 'options' in abargs:
            abtype = 'optionresponse'
        elif 'cfn' in abargs:
            abtype = 'customresponse'
        else:
            abtype = 'symbolicresponse'	# default
        
        abxml = etree.Element(abtype)

        if abtype=='optionresponse':
            self.require_args(['expect'])
            oi = etree.Element('optioninput')
            optionstr, options = self.get_options(abargs)
            oi.set('options',optionstr)
            oi.set('correct',self.stripquotes(abargs['expect']))
            abxml.append(oi)
            self.copy_attrib(abargs,'inline',abxml)
            
        if abtype=='multiplechoiceresponse':
            self.require_args(['expect','options'])
            cg = etree.SubElement(abxml,'choicegroup')
            cg.set('direction','vertical')
            optionstr, options = self.get_options(abargs)
            expect = self.stripquotes(abargs['expect'])
            cnt = 1
            for op in options:
                choice = etree.SubElement(cg,'choice')
                choice.set('correct','true' if op==expect else 'false')
                choice.set('name',str(cnt))
                choice.text = "<span> %s</span>" %op 
                cnt += 1

        elif abtype=='shortanswerresponse':
            print "[latex2html.abox] Warning - short answer response quite yet implemented in edX!"
            if 1:
                tb = etree.Element('textbox')
                self.copy_attrib(abargs,'rows',tb)
                self.copy_attrib(abargs,'cols',tb)
                abxml.append(tb)
                abxml.tag = 'customresponse'
                self.require_args(['expect','cfn'])
                abxml.set('cfn',self.stripquotes(abargs['cfn']))
                self.copy_attrib(abargs,'expect',abxml)
                
            else:
                abxml.tag = 'stringresponse'	# change to stringresponse for now (FIXME)
                tl = etree.Element('textline')
                tl.set('size','80')
                abxml.append(tl)
                abxml.set('answer','unknown')
                self.copy_attrib(abargs,'inline',tl)
                self.copy_attrib(abargs,'inline',abxml)
            
        elif abtype=='stringresponse':
            self.require_args(['expect'])
            tl = etree.Element('textline')
            if 'size' in abargs: tl.set('size',self.stripquotes(abargs['size']))
            abxml.append(tl)
            abxml.set('answer',self.stripquotes(abargs['expect']))
            self.copy_attrib(abargs,'inline',tl)
            self.copy_attrib(abargs,'inline',abxml)

        elif abtype=='customresponse':
            self.require_args(['expect','cfn'])
            abxml.set('cfn',self.stripquotes(abargs['cfn']))
            self.copy_attrib(abargs,'expect',abxml)
            tl = etree.Element('textline')
            self.copy_attrib(abargs,'size',tl)
            abxml.append(tl)
            tl.set('correct_answer',self.stripquotes(abargs['expect']))
            self.copy_attrib(abargs,'inline',tl)
            self.copy_attrib(abargs,'inline',abxml)
            
        elif abtype=='externalresponse' or abtype== 'coderesponse':
            if 'url' in abargs:
                self.copy_attrib(abargs,'url',abxml)
            tb = etree.Element('textbox')
            self.copy_attrib(abargs,'rows',tb)
            self.copy_attrib(abargs,'cols',tb)
            self.copy_attrib(abargs,'tests',abxml)
            abxml.append(tb)
            # turn script to <answer> later

        elif abtype=='numericalresponse':
            self.require_args(['expect'])
            self.copy_attrib(abargs,'inline',abxml)
            tl = etree.Element('textline')
            self.copy_attrib(abargs,'size',tl)
            self.copy_attrib(abargs,'inline',tl)
            self.copy_attrib(abargs,'math',tl)
            abxml.append(tl)
            self.copy_attrib(abargs,'options',abxml)
            answer = self.stripquotes(abargs['expect'])
            try:
                x = float(answer)
            except Exception as err:
                print "Error - numericalresponse expects numerical expect value, for %s" % s
                raise
            abxml.set('answer',answer)
            rp = etree.SubElement(tl,"responseparam")
            rp.attrib['description'] = "Numerical Tolerance"
            rp.attrib['type'] = "tolerance"
            rp.attrib['default'] = abargs.get('tolerance') or "0.00001"
            rp.attrib['name'] = "tol"
        
        elif abtype=='symbolicresponse':
            self.require_args(['expect'])
            self.copy_attrib(abargs,'expect',abxml)
            self.copy_attrib(abargs,'debug',abxml)
            self.copy_attrib(abargs,'options',abxml)
            tl = etree.Element('textline')
            self.copy_attrib(abargs,'inline',tl)
            self.copy_attrib(abargs,'size',tl)
            abxml.append(tl)
            self.copy_attrib(abargs,'inline',abxml)
            if 'correct_answer' in abargs:
                tl.set('correct_answer',self.stripquotes(abargs['correct_answer']))
            else:
                tl.set('correct_answer',self.stripquotes(abargs['expect']))
            tl.set('math','1')	# use dynamath
 
        # has hint function?
        if 'hintfn' in abargs:
            hintfn = self.stripquotes(abargs['hintfn'])
            hintgroup = etree.SubElement(abxml,'hintgroup')
            hintgroup.set('hintfn',hintfn)

        s = etree.tostring(abxml,pretty_print=True)
        s = re.sub('(?ms)<html>(.*)</html>','\\1',s)
        # print s
        return etree.XML(s)

    def get_options(self,abargs):
        optstr = abargs['options']			# should be double quoted strings, comma delimited
        #options = [c for c in csv.reader([optstr])][0]	# turn into list of strings
        options = split_args_with_quoted_strings(optstr, lambda(x): x==',')		# turn into list of strings
        options = map(self.stripquotes, options)
        options = [x.strip() for x in options]		# strip strings
        if "" in options: options.remove("")
        optionstr = ','.join(["'%s'" % x for x in options])	# string of single quoted strings
        optionstr = "(%s)" % optionstr				# enclose in parens
        return optionstr, options
    
    def require_args(self,argnames):
        for argname in argnames:
            if argname not in self.abargs:
                print "\n============================================================"
                print "Error - abox requires %s argument" % argname
                print "Answer box string is \"%s\"" % self.aboxstr
                # raise Exception, "Bad abox"
                sys.exit(0)
            
    def abox_args(self,s):
        '''
        Parse arguments of abox.  Splits by space delimitation.
        '''
        s = s.replace(u'\u2019',"'")
        try:
            s = str(s)
        except Exception, err:
            print "Error %s in obtaining string form of abox argument %s" % (err,s)
            return {}
        try:
            # abargstxt = shlex.split(s)
            abargstxt = split_args_with_quoted_strings(s)
        except Exception, err:
            print "Error %s in parsing abox argument %s" % (err,s)
            return {}

        if '' in abargstxt:
            abargstxt.remove('')
            
        try:
            abargs = dict([x.split('=',1) for x in abargstxt])
        except Exception, err:
            print "Error %s" % err
            print "Failed in parsing args = %s" % s
            print "abargstxt = %s" % abargstxt
            raise

        for arg in abargs:
            abargs[arg] = self.stripquotes(abargs[arg],checkinternal=True)

        return abargs

    def stripquotes(self,x,checkinternal=False):
        if x.startswith('"') and x.endswith('"'):
            if checkinternal and '"' in x[1:-1]:
                return x
            return x[1:-1]
        if x.startswith("'") and x.endswith("'"):
            return x[1:-1]
        return x

    def copy_attrib(self,abargs,aname,xml):
        if aname in abargs:
            xml.set(aname,self.stripquotes(abargs[aname]))

        
def split_args_with_quoted_strings(command_line, checkfn=None):

    """from pexpect.py
    This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """

    arg_list = []
    arg = ''

    if checkfn is None:
        def checkfn(c):
            return c.isspace()

    # Constants to name the states we can be in.
    state_basic = 0
    state_esc = 1
    state_singlequote = 2
    state_doublequote = 3
    # The state when consuming whitespace between commands.
    state_whitespace = 4
    state = state_basic

    for c in command_line:
        if state == state_basic or state == state_whitespace:
            if c == '\\':
                # Escape the next character
                state = state_esc
            elif c == r"'":
                # Handle single quote
                arg = arg + c
                state = state_singlequote
            elif c == r'"':
                # Handle double quote
                arg = arg + c
                state = state_doublequote
            elif checkfn(c):                  # OLD: c.isspace():
                # Add arg to arg_list if we aren't in the middle of whitespace.
                if state == state_whitespace:
                    # Do nothing.
                    None
                else:
                    arg_list.append(arg)
                    arg = ''
                    state = state_whitespace
            else:
                arg = arg + c
                state = state_basic
        elif state == state_esc:
            arg = arg + c
            state = state_basic
        elif state == state_singlequote:
            if c == r"'":
                arg = arg + c
                state = state_basic
            else:
                arg = arg + c
        elif state == state_doublequote:
            if c == r'"':
                arg = arg + c
                state = state_basic
            else:
                arg = arg + c

    if arg != '':
        arg_list.append(arg)
    return arg_list
