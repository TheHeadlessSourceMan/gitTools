"""
Tool to locate and incorporate any available git ui's
"""
import typing
import os
import k_runner.osrun as osrun


class _GitUi:
    """
    A single git ui

    Should go through GitUis object to get one of these!
    """

    def __init__(self,appLocation:str,sartIn=None):
        self.appLocation:str=appLocation
        self.sartIn:typing.Optional[str]=sartIn

    def run(self):
        """
        Run this ui
        """
        osrun.run(self.appLocation,detatch=True,workingDirectory=self.sartIn)

    def __call__(self):
        self.run()


class GitUis:
    """
    Tool to locate and incorporate any available git ui's

    TODO: expand PossibleUis such that a regular expression is allowed!

    TODO: could make this a generic application pool that would
        be more widely useful
    """

    PossibleUis=[ # (name,applocation match(es), startIn location match(es))
        ('githubdesktop',
         r'%appdata%\..\Local\GitHubDesktop\GitHubDesktop.exe',
         r'%appdata%\..\Local\GitHubDesktop\app-2.9.4'),
        ('sourcetree',
         r'%AppData%\..\Local\SourceTree\SourceTree.exe',
         r'%AppData%\..\Local\SourceTree\app-3.4.6'),
        ('fork',
         r'%AppData%\..\Local\Fork\Fork.exe',
         r'%AppData%\..\Local\Fork\app-1.75.0')
        ]

    def __init__(self):
        self.preferredOrder=['githubdesktop','sourcetree','fork']
        self.availableUis={}
        self._scan()

    @property
    def preferred(self):
        """
        Get the most preferred ui
        """
        for p in self.preferredOrder:
            if p in self.availableUis:
                return p
        raise Exception('No git UI\'s found!')

    def run(self,preferredUi:typing.Optional[str]=None):
        """
        Run a git ui
        """
        if preferredUi is None:
            preferredUi=self.preferred
        else:
            preferredUi=preferredUi.replace(' ','').lower()
            if preferredUi not in self.availableUis:
                preferredUi=self.preferred
        self.availableUis[preferredUi]()

    def __call__(self):
        self.run()

    def _scan(self):
        self.availableUis={}
        def checkOne(name,appLocation,startIn):
            appLocation=os.path.expandvars(appLocation)
            if not os.path.isfile(appLocation):
                return
            if startIn is not None:
                startIn=os.path.expandvars(startIn)
                if not os.path.isdir(startIn):
                    startIn=None
            self.availableUis[name]=_GitUi(appLocation,startIn)
        for name,appLocation,startIn in self.PossibleUis:
            checkOne(name,appLocation,startIn)

    def __repr__(self):
        ret=['Available git UI\'s:']
        ret.extend(self.availableUis.keys())
        return '\n   '.join(ret)

#print(GitUis())
