import os
import re

from gub import mirrors
from gub import repository
from gub import misc
from gub import targetbuild
from gub import context

class Ghostscript (targetbuild.TargetBuild):
    '''The GPL Ghostscript PostScript interpreter
Ghostscript is used for PostScript preview and printing.  It can
display PostScript documents in an X11 environment.  It can render
PostScript files as graphics to be printed on non-PostScript printers.
Supported printers include common dot-matrix, inkjet and laser
models.'''

    #subversion is broken, this also works but gives less nice results
    #source = 'svn:http://svn.ghostscript.com:8080/ghostscript/trunk/gs&revision=7881'
    # this does not yet work
    # source = 'svn:http://svn.ghostscript.com:8080/ghostscript&branch=trunk&module=gs&revision=7881'
    source = 'svn:http://svn.ghostscript.com:8080/ghostscript&branch=trunk/gs&revision=7881'
    #source = 'ftp://mirror.cs.wisc.edu/pub/mirrors/ghost/GPL/gs860/ghostscript-8.60.tar.bz2'
    def __init__ (self, settings, source):
        targetbuild.TargetBuild.__init__ (self, settings, source)

        ## ugh: nested, with self shadow?
        def version_from_VERSION (self):
            s = self.read_file ('src/version.mak')
            d = misc.grok_sh_variables_str (s)
            v = '%(GS_VERSION_MAJOR)s.%(GS_VERSION_MINOR)s' % d
            return v

        if (isinstance (source, repository.Repository)
            and not isinstance (source, repository.TarBall)):
            from new import instancemethod
            source.version = instancemethod (version_from_VERSION, source, type (source))

    def force_sequential_build (self):
        return True
    
    def get_build_dependencies (self):
        return ['libjpeg-devel', 'libpng-devel']

    def get_dependency_dict (self):
        return {'': ['libjpeg', 'libpng']}

    def get_subpackage_names (self):
        return ['doc', '']
    
    def srcdir (self):
        return re.sub ('-source', '',
                       targetbuild.TargetBuild.srcdir (self))

    def builddir (self):
        return re.sub ('-source', '',
                       targetbuild.TargetBuild.builddir (self))

    def name (self):
        return 'ghostscript'

    # FIXME: C&P.
    def ghostscript_version (self):
        return '.'.join (self.ball_version.split ('.')[0:2])

    def patch (self):
        disable_re = ('(DEVICE_DEVS[0-9]+)=([^\n]+(%s))'
                      % '|'.join (['tiff', 'pcx', 'uniprint',
                                   'deskjet', 'djet500', 'bmp', 'pbm',
                                   'bjc200', 'cdeskjet', 'faxg3', 'cljet5']))
        ## generate Makefile.in
        self.system ('cd %(srcdir)s && ./autogen.sh --help')
        self.file_sub ([(disable_re, r'#\1= -DISABLED- \2 ')],
                       '%(srcdir)s/Makefile.in')
        
    def fixup_arch (self):
        # FIXME: wow, this is broken, cross-compile-wise.  Use a compiled
        # c program to determine the size of basic types *after* an
        # autoconf run.  Should see if afpl ghostscript also uses autoconf
        # and send a patch that generates arch.h from configure.

        cache_size = 1024*1024
        big_endian = 0
        can_shift = 1
        align_long_mod = 4
        align_ptr_mod = 4
        log2_sizeof_long = 2
        sizeof_ptr = 4
        
        if 'powerpc' in self.settings.target_architecture:
            big_endian = 1
            can_shift = 1
            cache_size = 2097152
        elif re.search ('i[0-9]86', self.settings.target_architecture):
            big_endian = 0
            can_shift = 0
            cache_size = 1048576

        if '64' in self.settings.target_architecture:
            align_long_mod = 8
            align_ptr_mod = 8
            log2_sizeof_long = 3
            sizeof_ptr = 8

        self.file_sub (
            [('#define ARCH_CAN_SHIFT_FULL_LONG .',
              '#define ARCH_CAN_SHIFT_FULL_LONG %(can_shift)d' % locals ()),
             ('#define ARCH_CACHE1_SIZE [0-9]+',
              '#define ARCH_CACHE1_SIZE %(cache_size)d' % locals ()),
             ('#define ARCH_IS_BIG_ENDIAN [0-9]',
              '#define ARCH_IS_BIG_ENDIAN %(big_endian)d' % locals ()),
             ('#define ARCH_ALIGN_LONG_MOD [0-9]',
              '#define ARCH_ALIGN_LONG_MOD %(align_long_mod)d' % locals ()),
             ('#define ARCH_ALIGN_PTR_MOD [0-9]',
              '#define ARCH_ALIGN_PTR_MOD %(align_ptr_mod)d' % locals ()),
             ('#define ARCH_LOG2_SIZEOF_LONG [0-9]',
              '#define ARCH_LOG2_SIZEOF_LONG %(log2_sizeof_long)d' % locals ()),
             ('#define ARCH_SIZEOF_PTR [0-9]',
              '#define ARCH_SIZEOF_PTR %(sizeof_ptr)d' % locals ()),
             ], '%(builddir)s/obj/arch.h')

    def compile_command (self):
        return (targetbuild.TargetBuild.compile_command (self)
                + ' INCLUDE=%(system_prefix)s/include'
                + ' PSDOCDIR=%(prefix_dir)s/share/doc'
                + ' PSMANDIR=%(prefix_dir)s/share/man')
        
    def compile (self):
        self.system ('''
cd %(builddir)s && mkdir -p obj
cd %(builddir)s && make CC=cc CCAUX=cc C_INCLUDE_PATH= CFLAGS= CPPFLAGS= GCFLAGS= LIBRARY_PATH= obj/genconf obj/echogs obj/genarch obj/arch.h
''')
        self.fixup_arch ()
        targetbuild.TargetBuild.compile (self)
        
    def configure_command (self):
        return (targetbuild.TargetBuild.configure_command (self)
            + misc.join_lines ('''
--enable-debug
--with-drivers=FILES
--without-x
--disable-cups
--without-ijs
--without-omni
--without-jasper
--disable-compile-inits
'''))

    def configure (self):
        targetbuild.TargetBuild.configure (self)
        self.makefile_fixup ('%(builddir)s/Makefile')

    def makefile_fixup (self, file):
        self.file_sub ([
            ('-Dmalloc=rpl_malloc', ''),
            ('GLSRCDIR=./src', 'GLSRCDIR=%(srcdir)s/src'),
            ('PSSRCDIR=./src', 'PSSRCDIR=%(srcdir)s/src'),
            ('PSLIBDIR=./lib', 'PSLIBDIR=%(srcdir)s/lib'),
            ('ICCSRCDIR=icclib', 'ICCSRCDIR=%(srcdir)s/icclib'),
            ('IJSSRCDIR=src', 'IJSSRCDIR=%(srcdir)s/src'),
            ('IMDISRCDIR=imdi', 'IMDISRCDIR=%(srcdir)s/imdi'),
            ('CONTRIBDIR=./contrib', 'CONTRIBDIR=%(srcdir)s/contrib'),
            ('include contrib/', 'include %(srcdir)s/contrib/'),
            # ESP-specific: addonsdir, omit zillion of
            # warnings (any important ones may be noticed
            # easier).
            ('ADDONSDIR=./addons', 'ADDONSDIR=%(srcdir)s/addons'),
            (' -Wmissing-prototypes ', ' '),
            (' -Wstrict-prototypes ', ' '),
            (' -Wmissing-declarations ', ' '),

            ## ugh:  GS compile adds another layer of shell expansion. Yuck.
            (r'\$\${ORIGIN}', '\\$${ORIGIN}'),
            ],
               file)

    def install_command (self):
        return (targetbuild.TargetBuild.install_command (self)
                + ' install_prefix=%(install_root)s'
                + ' mandir=%(prefix_dir)s/share/man/ '
                + ' docdir=%(prefix_dir)s/share/doc/ghostscript/doc '
                + ' exdir=%(prefix_dir)s/share/doc/ghostscript/examples '
                )

    def install (self):
        targetbuild.TargetBuild.install (self)
        self.system ('mkdir -p %(install_prefix)s/etc/relocate/')
        self.dump ('''

prependdir GS_FONTPATH=$INSTALLER_PREFIX/share/ghostscript/%(version)s/fonts
prependdir GS_FONTPATH=$INSTALLER_PREFIX/share/gs/fonts
prependdir GS_LIB=$INSTALLER_PREFIX/share/ghostscript/%(version)s/Resource
prependdir GS_LIB=$INSTALLER_PREFIX/share/ghostscript/%(version)s/lib

''', '%(install_prefix)s/etc/relocate/gs.reloc')

class Ghostscript__mingw (Ghostscript):
    def __init__ (self, settings, source):
        Ghostscript.__init__ (self, settings, source)
        # Configure (compile) without -mwindows for console
        # FIXME: should add to CPPFLAGS...
        self.target_gcc_flags = '-mms-bitfields -D_Windows -D__WINDOWS__'

    def patch (self):
        Ghostscript.patch (self)
        self.system ('''
#checkme, seems obsolete, is this still necessary?
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.15-cygwin.patch
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.15-windows-wb.patch
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.50-make.patch
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.50-gs_dll.h.patch
''')
        self.file_sub ([('unix__=$(GLOBJ)gp_getnv.$(OBJ) $(GLOBJ)gp_unix.$(OBJ) $(GLOBJ)gp_unifs.$(OBJ) $(GLOBJ)gp_unifn.$(OBJ) $(GLOBJ)gp_stdia.$(OBJ) $(GLOBJ)gp_unix_cache.$(OBJ)',
                         'unix__= $(GLOBJ)gp_mswin.$(OBJ) $(GLOBJ)gp_wgetv.$(OBJ) $(GLOBJ)gp_stdia.$(OBJ) $(GLOBJ)gsdll.$(OBJ) $(GLOBJ)gp_ntfs.$(OBJ) $(GLOBJ)gp_win32.$(OBJ)')],
                       '%(srcdir)s/src/unix-aux.mak',
                       use_re=False, must_succeed=True)
#        self.system ('cd %(srcdir)s/ && patch --force -p1 < %(patchdir)s/ghostscript-8.50-unix-aux.mak.patch')

    def configure (self):
        Ghostscript.configure (self)
        # FIXME: use makeflags: EXTRALIBS=... ?
        self.file_sub ([('^(EXTRALIBS *=.*)', '\\1 -lwinspool -lcomdlg32 -lz')],
               '%(builddir)s/Makefile')

        self.file_sub ([('^unix__=.*', misc.join_lines ('''unix__=
$(GLOBJ)gp_mswin.$(OBJ)
$(GLOBJ)gp_wgetv.$(OBJ)
$(GLOBJ)gp_stdia.$(OBJ)
$(GLOBJ)gsdll.$(OBJ)
$(GLOBJ)gp_ntfs.$(OBJ)
$(GLOBJ)gp_win32.$(OBJ)
'''))],
               '%(srcdir)s/src/unix-aux.mak')
        self.file_sub ([('^(LIB0s=.*)', misc.join_lines ('''\\1
$(GLOBJ)gp_mswin.$(OBJ)
$(GLOBJ)gp_wgetv.$(OBJ)
$(GLOBJ)gp_stdia.$(OBJ)
$(GLOBJ)gsdll.$(OBJ)
$(GLOBJ)gp_ntfs.$(OBJ)
$(GLOBJ)gp_win32.$(OBJ)
'''))],
               '%(srcdir)s/src/lib.mak')

        self.dump ('''
GLCCWIN=$(CC) $(CFLAGS) -I$(GLOBJDIR)
PSCCWIN=$(CC) $(CFLAGS) -I$(GLOBJDIR)
include $(GLSRCDIR)/win32.mak
include $(GLSRCDIR)/gsdll.mak
include $(GLSRCDIR)/winplat.mak
include $(GLSRCDIR)/pcwin.mak
''',
             '%(builddir)s/Makefile',
             mode='a')

    def install (self):
        Ghostscript.install (self)

class Ghostscript__freebsd (Ghostscript):
    def get_dependency_dict (self):
        d = Ghostscript.get_dependency_dict (self)
        d[''].append ('libiconv')
        return d

url='http://mirror3.cs.wisc.edu/pub/mirrors/ghost/GPL/gs860/ghostscript-8.60.tar.gz'
url='http://mirror3.cs.wisc.edu/pub/mirrors/ghost/GPL/gs850/ghostscript-8.50-gpl.tar.gz'
#8250
fonts_url = 'http://mirror2.cs.wisc.edu/pub/mirrors/ghost/GPL/gs860/ghostscript-fonts-std-8.11.tar.gz'
class Ghostscript__cygwin (Ghostscript):
    def __init__ (self, settings, source):
        Ghostscript.__init__ (self, settings, source)
        #self.source.revision = '8250'
        #targetbuild.TargetBuild.__init__ (self, settings, source)
        #self.with_vc (repository.TarBall (self.settings.downloads, url))
        self.fonts_source = repository.TarBall (self.settings.downloads,
                                                fonts_url)
    def connect_command_runner (self, runner):
        self.fonts_source.connect_command_runner (runner)
        return Ghostscript.connect_command_runner (self, runner)
    def download (self):
        Ghostscript.download (self)
        self.fonts_source.download ()
    def patch (self):
        from gub import cygwin
        cygwin.libpng12_fixup (self)
        self.system ('''
cd %(srcdir)s && ./autogen.sh --help
cd %(srcdir)s && cp Makefile.in Makefile-x11.in
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.15-windows-wb.patch
cd %(srcdir)s/ && patch -p1 < %(patchdir)s/ghostscript-8.57-cygwin-esp.patch
''')
    def category_dict (self):
        return {'': 'Graphics'}
    def get_build_dependencies (self):
        return ['jpeg', 'libpng12-devel', 'xorg-x11-devel', 'zlib']
    def get_dependency_dict (self):
        return {'': [
                # REMOVE after first cygwin release.
                'ghostscript-base',
                'libjpeg62', 'libpng12', 'zlib'],
                'x11': ['ghostscript', 'xorg-x11-base']}
    def get_subpackage_names (self):
        return ['doc', 'x11', '',
                # REMOVE after first cygwin release.
                'base']
    # REMOVE after first cygwin release.
    def get_subpackage_definitions (self):
        d = Ghostscript.get_subpackage_definitions (self)
        d['base'] = []
        return d
    def configure_command (self):
        return (Ghostscript.configure_command (self)
                .replace (' --with-drivers=FILES', ' --with-drivers=ALL'))
    def compile (self):
        self.system ('''
mkdir -p %(builddir)s
cd %(builddir)s && rm -f obj/*.tr
''')
        Ghostscript.compile (self)
# X11 stuff
    def stages (self):
        return misc.list_insert_before (Ghostscript.stages (self),
                                        'package',
                                        ['configure_x11', 'compile_x11',
                                         'install_x11', 'install_fonts'])
    def config_cache (self):
        Ghostscript.config_cache (self)
        self.system ('cd %(builddir)s && cp -p config.cache config-x11.cache')
    @context.subst_method
    def configure_command_x11 (self):
        return ('CONFIG_FILES=Makefile-x11'
                + ' CONFIG_STATUS=config-x11.status'
                + ' ' + self.configure_command ()
                .replace ('--without-x', '--with-x')
                .replace ('--config-cache', '--cache-file=config-x11.cache')
                + ' --x-includes=%(system_prefix)s/X11R6/include'
                + ' --x-libraries=%(system_prefix)s/X11R6/lib'
                + ' Makefile')
    def configure_x11 (self):
        self.system ('''
mkdir -p %(builddir)s
cd %(builddir)s && %(configure_command_x11)s
''')
        self.makefile_fixup ('%(builddir)s/Makefile-x11')
    @context.subst_method
    def compile_command_x11 (self):
        return Ghostscript.compile_command (self) + ' -f Makefile-x11 GS=gs-x11.exe'
    def compile_x11 (self):
        self.system ('''
cd %(builddir)s && rm -f obj/*.tr
cd %(builddir)s && %(compile_command_x11)s
''')
    @context.subst_method
    def install_command_x11 (self):
        return (Ghostscript.install_command (self)
                .replace (' install ', ' install-exec ')
                + ' -f Makefile-x11 GS=gs-x11.exe prefix=/usr/X11R6')
    def install_x11 (self):
        self.system ('''
cd %(builddir)s && %(install_command_x11)s
cd %(install_prefix)s && rm -rf usr/X11R6/share
''')
    def install_fonts (self):
        fontdir = self.expand ('%(install_prefix)s/share/ghostscript/fonts')
        self.fonts_source.update_workdir (fontdir)
    def makeflags (self):
        # Link to binmode to fix text mode mount problem
        # http://cygwin.com/ml/cygwin/2002-07/msg02302.html
        # although text mode mounts are considered evil...
        return ' CFLAGS_STANDARD="-g -O2" EXTRALIBS=-lbinmode'
    # REMOVE after first cygwin release.
    def description_dict (self):
        return {'base': 'The GPL Ghostscript PostScript interpreter - transitional package\nThis is an empty package to streamline the upgrade.'}
