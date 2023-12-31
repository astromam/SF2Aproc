#!/usr/bin/env python3


## by A. Mennucci

## starting from
## https://tex.stackexchange.com/a/23438/199657
## ( adapted to Python3)

## added support for characters with multiple accents,
## https://unicode.org/reports/tr15/tr15-27.html

##  and many decompositions
## https://www.compart.com/en/unicode/decomposition/

"""
This script will convert unicode to a suitable LaTeX representation.
It will convert accents, e.g. è  → \`{e} .
It will express fonts, e.g.  ⅅ → \symbbit{D} .
It will convert math symbols, e.g.  ∩ → \cap .
"""

import os, sys, copy, io, argparse, unicodedata, collections, subprocess, logging
logger = logging.getLogger(__name__)

verbose = 0

prefer_unicode_math = False

unicode_math_file = '/usr/share/texlive/texmf-dist/tex/latex/unicode-math/unicode-math-table.tex'

try:
    p = subprocess.Popen(['kpsewhich', 'unicode-math-table.tex'], stdout=subprocess.PIPE)
    a = p.stdout.read().strip()
    p.wait()
    if os.path.isfile(a):
        unicode_math_file = a
    else:
        logger.warning('Cannot locate unicode-math-table.tex')
except:
    logger.exception('While running kpsewhich unicode-math-table.tex')

math2latex = {
    0xD7 : '\\times',
    0x221E : '\\infty',
    0xab : '\\guillemotleft' , 0xbb : '\\guillemotright',
}


## see also
## https://ctan.math.washington.edu/tex-archive/fonts/kpfonts-otf/doc/unimath-kpfonts.pdf

if os.path.isfile(unicode_math_file):
    for s in open(unicode_math_file):
        if s.startswith('\\UnicodeMathSymbol'):
            s = s.split('{')
            code=int(s[1].lstrip('"').rstrip('}').rstrip(' '),16)
            latex=s[2].rstrip('}').rstrip(' ')
            if code not in math2latex: 
                math2latex[code] = latex
            elif verbose:
                sys.stderr.write('(Prefer %r for %x to %r )\n' % (math2latex[code], code,latex))



accents = {
    0x0300: '`', 0x0301: "'", 0x0302: '^', 0x0308: '"',
    0x030B: 'H', 0x0303: '~', 0x0327: 'c', 0x0328: 'k',
    0x0304: '=', 0x0331: 'b', 0x0307: '.', 0x0323: 'd',
    0x030A: 'r', 0x0306: 'u', 0x030C: 'v',
}

##https://ctan.mirror.garr.it/mirrors/ctan/macros/unicodetex/latex/unicode-math/unicode-math.pdf
##table 7
fonts = (
    ('SANS-SERIF BOLD ITALIC', '\\symbfsfit'),
    ('SANS-SERIF BOLD',        '\\symbfit'),
    ('SANS-SERIF ITALIC',      '\\symsfit'),
    ('BOLD ITALIC',  '\\symbfit'),
    ## currently broken
    #('BOLD FRAKTUR', '\\symbffrac'),
    ('BOLD SCRIPT',  '\\symbfscr'),
    ('DOUBLE-STRUCK ITALIC',  '\\symbbit'),
    #
    ('DOUBLE-STRUCK',  '\\symbb'),
    ('BLACK-LETTER',   '\\symfrak'),
    ('FRAKTUR',        '\\symfrak'),
    ('SANS-SERIF',     '\\symsf'),
    ('MONOSPACE',      '\\symtt'),
    ('SCRIPT',         '\\symscr'),
    ('BOLD',           '\\symbf'),
    ('ITALIC',         '\\symit'),
    )
    

modifiers = {
    '<super>': '^{%s}' , '<sub>' : '_{%s}',
}


line_count = 1
char_count = 0
input_file = 'cmdline'


def decompose_to_tex(text, output):
    global char_count
    if isinstance(text,str):
        assert(len(text) == 1)
        char = text
    else:
    #if isinstance(text,  collections.abc.Iterable):
        char = next(text)
        char_count += 1
    code = ord(char)
    cat = unicodedata.category(char)
    dec = unicodedata.decomposition(char)
    name = unicodedata.name(char, '')
    #
    if prefer_unicode_math and code in math2latex and code > 0x7f:
        latex = math2latex[code]
        if verbose: sys.stderr.write('%r:%d:%d math %r %x %s\n' % (input_file, line_count, char_count,char,code,latex))
        output.append(latex+' ')
        return
    #
    if (verbose and dec) or (verbose > 1 ):
        sys.stderr.write('%r:%d:%d decomposing %r %x %r %r %r\n' % (input_file, line_count, char_count,char,code,cat,dec,name))
    #
    if cat in ("Mn", "Mc") and code in accents:
        try:
            n = output.pop()
        except IndexError:
            sys.stderr.write('%r:%d:%d accents with no preceding character\n' % (input_file, line))
            n=' '
        output.append( "\\%s{%s}" %(accents[code], n) )
        return
    
    if dec:
        if dec.startswith('<fraction>'):
            dec =  dec.split()[1:]
            dec = list(map(lambda x : chr(int(x,16)), dec))
            if dec[-1] == '/': dec[-1] = ''
            output.append( '{\sfrac{%s}{%s}}' % (dec[0],dec[-1]))
            return
        decsplit = dec.split()
        base, acc = decsplit[:2]
        if base == '<font>':
            mod = '%s'
            N = copy.copy(name)
            for s,l in fonts:
                if s in N:
                    #print((s,N))
                    mod = l + '{' +  mod + '}'
                    j = N.index(s)
                    N = N[:j] + N[j+len(s):]
                    #print((s,N))
            acc = int(acc, 16)
            decompose_to_tex(chr(acc), output)
            n = output.pop()
            output.append( mod % n )
            return
        if base == '<small>':
            acc = int(acc, 16)
            decompose_to_tex(chr(acc), output)
            n = output.pop()
            output.append( '{\scriptsize{%s}}' % n )
            return
        if base == '<compat>':
            # greek characters, `var` version
            acc = int(acc, 16)
            if 0x370 <= acc <= 0x3ff:
                decompose_to_tex(chr(acc), output)
                n = output.pop()
                output.append( n[0] + 'var' + n[1:] )
                return
            elif 'LIGATURE' in name:
                for l in decsplit[1:]:
                    l = int(l, 16)
                    decompose_to_tex(chr(l), output)
                return
            sys.stderr.write('%r:%d:%d unsupported <compat> %r\n' % (input_file, line_count, char_count,dec))
        elif base in modifiers:
            mod = modifiers[base]
            acc = int(acc, 16)
            decompose_to_tex(chr(acc), output)
            n = output.pop()
            output.append( mod % n )
            return
        elif base.startswith('<'):
            sys.stderr.write('%r:%d:%d unsupported modifier %r\n' % (input_file, line_count, char_count,base))
            #acc = int(acc, 16)
            #decompose_to_tex(chr(acc), output)
            #n = output.pop()
            #output.append( mod % n )
            output.append(char)
            return
        try:
            base = int(base, 16)
            acc = int(acc, 16)
            if acc in accents:
                decompose_to_tex(chr(base), output)
                n = output.pop()
                output.append( "\\%s{%s}" %(accents[acc], n) )
                return
        except ValueError:
            sys.stderr.write('%r:%d:%d unsupported decomposition %r\n' % (input_file, line_count, char_count,dec))
    #
    if name.startswith('GREEK'):
        char = name.split()[-1].lower()
        if 'SMALL' not in name:
            char = char[0].upper() + char[1:]
        output.append('\\' + char)
        return
    #
    if code in math2latex and code > 0x7f:
        latex = math2latex[code]
        if verbose: sys.stderr.write('%r:%d:%d math %r %x %s\n' % (input_file, line_count, char_count,char,code,latex))
        output.append(latex+' ')
        return
    if code > 127:
        sys.stderr.write('%r:%d:%d could not convert %r %x to ascii\n' % (input_file, line_count, char_count,char,code))
    output.append(char)
        
def uni2tex(text):
    iterable = iter(text)
    output = []
    try:
        while True:
            decompose_to_tex(iterable, output)
    except StopIteration:
        pass
    return ''.join(output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='convert Unicode to LaTeX',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     epilog=__doc__)
    parser.add_argument('--verbose','-v',action='count',default=verbose)
    parser.add_argument('--prefer-unicode-math','-P',action='store_true',
                        default=prefer_unicode_math,
                        help='converto to unicode-math commands whenever possible')
    parser.add_argument('--output','-o',
                        help='output file')
    parser.add_argument('--input','-i',
                        help='read input file')
    parser.add_argument('--stdin',action='store_true',
                        help='read stdin (instead of input file)')
    parser.add_argument('text', nargs='*',
                        help='the unicode text')
    args = parser.parse_args()
    #
    if 1 != bool(args.text) + bool(args.input) + bool(args.stdin):
        parser.print_help()
        sys.exit(1)
    #
    verbose = args.verbose
    prefer_unicode_math = args.prefer_unicode_math
    #
    if args.input or args.stdin:
        out=sys.stdout
        if args.output:
            out = open(args.output, 'w')
        if args.text:
            logger.warning('Cmdline %r ignored', args.text)
        if args.stdin:
            input_file = 'stdin'
            for L in sys.stdin:
                out.write(uni2tex(L))
                char_count = 0
                line_count += 1
        else:
            input_file = args.input
            for L in open(args.input):
                out.write(uni2tex(L))
                char_count = 0
                line_count += 1
        sys.exit(0)
    #
    for  t in args.text:
        if not isinstance(t,str):
            t = str(t, "utf-8")
        print(uni2tex(t))
    sys.exit(0)
    
