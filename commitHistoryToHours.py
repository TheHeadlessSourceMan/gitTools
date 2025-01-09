"""
The purpose of this is to scan the commit history for
one or more git projects and, based on file type, hours per line,
and pay rate per file type, come up with a cost estimate.
"""
import typing
import datetime
from paths import Url,UrlCompatible,asUrl
from commits import gitLog


Money=float


class FileRate:
    """
    Track what rate should be used for files matching a given pattern
    """
    def __init__(self,
        filenameMatch:typing.Pattern,
        hourlyRate:Money,
        hoursPerLine:float=1.0,
        name:str=''):
        """ """
        self.name:str=name
        self.filenameMatch:typing.Pattern=filenameMatch
        self.hourlyRate:Money=hourlyRate
        self.hoursPerLine:float=hoursPerLine

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


class BillLineItem:
    """
    A single entry on the receipt
    """
    def __init__(self,
        name:str,
        date:datetime.datetime,
        numLines:int,
        rate:FileRate,
        link:typing.Optional[UrlCompatible]):
        """ """
        self.name=name
        self.date=date
        self.numLines=numLines
        self.rate:FileRate=rate
        if link is None:
            self.link=None
        else:
            self.link=asUrl(link)

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
        return self.rate.hoursPerLine*self.numLines*self.rate.hourlyRate

    @property
    def html(self):
        """
        Full html breakdown
        """
        date=self.date.strftime('%D/%M/%Y %H:%m%p')
        name=self.name
        if self.link is not None:
            name=f'<a href="{self.link}">{name}</a>'
        cols=[name,date,
            f'{self.hours}hr @{self.rate.hourlyRate}',f'${self.amount}']
        return '<tr><td>'+('</td><td>'.join(cols))+'</td></tr>'

    def __repr__(self):
        date=self.date.strftime('%D/%M/%Y %h:%m:%s %p')
        return f"{self.name}   {date}  {self.hours}hr @{self.rate.hourlyRate}   {self.amount}" # noqa: E501 # pylint: disable=line-too-long


class Bill:
    """
    A full bill
    """
    def __init__(self):
        self.lineItems:typing.List[BillLineItem]=[]

    @property
    def subtotal(self)->float:
        """
        Sum of all the line items
        """
        return sum(item.amount for item in self.lineItems)

    def __iter__(self)->typing.Iterator[BillLineItem]:
        return iter(self.lineItems)

    def append(self,
        items:typing.Union[BillLineItem,typing.Iterable[BillLineItem]]):
        """
        Add one or more items to the bill
        """
        if isinstance(items,BillLineItem):
            self.lineItems.append(items)
        else:
            self.lineItems.extend(items)
    extend=append
    add=append

    @property
    def html(self):
        """
        Get a full html breakdown
        """
        ret='\n'.join(item.html for item in self)
        return f'<table>{ret}<tr></tr><tr><td></td><td></td><td>SUBTOTAL</td><td>{self.subtotal}</td></tr></table>' # noqa: E501 # pylint: disable=line-too-long

    def __repr__(self):
        ret='\n'.join(repr(item) for item in self)
        return f'{ret}\n\t=====================\n\tSUBTOTAL\t{self.subtotal}'

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
            if f.filenameMatch.match(filename) is not None:
                return f
        raise FileNotFoundError(f'Unknown file type for "{filename}". You should at least have a ".*" type registered!') # noqa: E501 # pylint: disable=line-too-long

    def calculate(self)->Bill:
        """
        Run the calculation
        """
        bill=Bill()
        for repoPath in self.gitFolders:
            commits=gitLog(repoPath)
            for commit in commits:
                diff=commit.diff
                date=diff.date
                for fileDiff in diff:
                    numLines=fileDiff.numLines
                    rate=self.getFileRate(fileDiff.filename)
                    name=fileDiff.filename
                    link=fileDiff.githubUrl
                    bill.append(BillLineItem(name,date,numLines,rate,link))
        return bill

def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    import re
    ch2h=CommitHistoryToHours([])
    html=True # TODO: False
    gotFolder=False
    printHelp=False
    fileRate=FileRate(re.compile('.*'),5.5) # TODO: temporary, for testing
    ch2h.fileRates.append(fileRate)
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            avl=av[0].lower()
            if avl=='-h':
                printHelp=True
            elif avl=='--html':
                html=True
            elif avl=='--rate':
                fr=av[1].split('=',1)
                if len(fr)<2:
                    fileRate=FileRate(
                        re.compile('.*'),
                        float(fr[0].replace('$','').strip()))
                else:
                    fileRate=FileRate(
                        re.compile(fr[0]),
                        float(fr[1].replace('$','').strip()))
                ch2h.fileRates.append(fileRate)
            else:
                printHelp=True
        else:
            ch2h.gitFolders.append(arg)
            gotFolder=True
    if not printHelp:
        if not gotFolder:
            ch2h.gitFolders.append('.')
        result=ch2h.calculate()
        if html:
            print(result.html)
        else:
            print(result)
    else:
        print('USAGE:')
        print('  commitHistoryToHours [options] [checkout_folder]')
        print('OPTIONS:')
        print('  -h .......................... this help')
        print('  --html ...................... full breakdown in html')
        print('  --rate=[fileRe=]costPerLine . billing rate for a file type')
        print('     (evaluated in order)')
        print('CHECKOUT FOLDER:')
        print('  local folder where the git repo is checked out')
        print('  (IMPORTANT: do a git pull before running this!)')
        return 1
    return 0


if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))
