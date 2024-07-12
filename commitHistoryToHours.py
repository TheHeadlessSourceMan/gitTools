"""
The purpose of this is to scan the commit history for
one or more git projects and, based on file type, hours per line,
and pay rate per file type, come up with a cost estimate.
"""
import typing
import datetime
from paths import Url,UrlCompatible,asUrl


Money=float


class FileRate:
    """
    Track what rate should be used for files matching a given pattern
    """
    def __init__(self):
        self.name:str
        self.filenameMatch:typing.Pattern
        self.hourlyRate:Money
        self.hoursPerLine:float

        @property
        def hourlyRatePerLine(self)->Money:
            """
            How much does each line cost
            """
            return self.hourlyRate/self.hoursPerLine


class HoursPerFileRate:
    """
    Result containing how many total hours were spent on each file type
    """
    def __init__(self):
        self.hours:float=0
        self.FileRate:str


class RecieptEntry:
    """
    A single entry on the receipt
    """
    def __init__(self,date:datetime.datetime,numLines:int,rate:FileRate):
        self.date=date
        self.numLines=numLines
        self.rate=rate

    @property
    def hours(self)->float:
        """
        How many hours this line represents
        """
        return self.rate.hoursPerLine*self.numLines

    @property
    def amount(self)->Money:
        """
        How much money this line represents
        """
        return self.rate.self.hourlyRatePerLine*self.numLines

    def __repr__(self):
        return f"{self.date}   {self.hours}hr @{self.rate.hourlyRate}   {self.amount}" # noqa: E501


class CommitHistoryToHours:
    """
    The purpose of this is to scan the commit history for
    one or more git projects and, based on file type, hours per line,
    and pay rate per file type, come up with a cost estimate.
    """

    def __init__(self,
        gitFolders:typing.Union[UrlCompatible,typing.Iterable[UrlCompatible]]):
        """ """
        if isinstance(gitFolders,(str,Url)) \
            or not hasattr(gitFolders,"__iter__"):
            gitFolders=(gitFolders,)
        self.gitFolders:typing.List[Url]=[asUrl(url) for url in gitFolders]
        self.fileRates:typing.List[FileRate]=[] # searched IN ORDER! There should always be a ".* at the end # noqa: E501 # pylint: disable=line-too-long

    def getFileRate(self,filename:str)->FileRate:
        """
        Get a FileRate for a given file
        """
        for f in self.fileRates:
            if f.match(filename):
                return f
        raise FileNotFoundError(f'Unknown file type for "{filename}". You should at least have a ".*" type registered!') # noqa: E501 # pylint: disable=line-too-long

    def calculate(self):
        """
        Run the calculation
        """
