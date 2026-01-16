"""
A single difference within a diff file

NOTE: this can have a number of changes within it
"""
import typing
from enum import IntEnum
from paths import Url
from .change import ChangeLocation,ChangeLocationType
if typing.TYPE_CHECKING:
    from .diff import FileDifferences


class DifferenceType(IntEnum):
    """
    Enum to indicate what type of change
    a difference represents
    """
    TYPE_NONE=0
    TYPE_ADD=1
    TYPE_REMOVE=2
    TYPE_UPDATE=3
    TYPE_MODIFY=3


class Difference:
    """
    A single difference within a diff file

    NOTE: this can have a number of changes within it
    """

    def __init__(self,fileDifferences:'FileDifferences',data:str):
        self.fileDifferences:'FileDifferences'=fileDifferences
        self.differenceType:DifferenceType=DifferenceType.TYPE_NONE
        self.before:typing.List[ChangeLocation]=[]
        self.beforeWithContext:typing.Optional[ChangeLocation]=None
        self.after:typing.List[ChangeLocation]=[]
        self.afterWithContext:typing.Optional[ChangeLocation]=None
        self.assign(data)

    def getChangeLocations(self,
        before:bool=False,
        after:bool=True
        )->typing.Generator[ChangeLocation,None,None]:
        """
        Get all changes
        """
        if before:
            yield from self.before
        if after:
            yield from self.after
    getChanges=getChangeLocations

    @property
    def parent(self)->'FileDifferences':
        """
        File differences
        """
        return self.fileDifferences

    @property
    def scope(self)->str:
        """
        diff scope string, eg:
            @@ -2848,7 +2848,7 @@
        """
        return f'@@ -{self.removedScopeStartLine},{self.removedScopeNumLines} +{self.addedScopeStartLine},{self.addedScopeNumLines} @@' # noqa: E501 # pylint: disable=line-too-long
    @scope.setter
    def scope(self,line:str):
        locationScope=line.split('@@',2)[1].strip().split()
        removedScope=locationScope[0][1:].split(',')
        addedScope=locationScope[1][1:].split(',')
        self.removedScopeStartLine=int(removedScope[0])
        self.removedScopeNumLines=int(removedScope[1])
        self.addedScopeStartLine=int(addedScope[0])
        self.addedScopeNumLines=int(addedScope[1])

    @property
    def removedScopeEndLine(self):
        """
        End line for the entire scope
        """
        return self.removedScopeStartLine+self.removedScopeEndLine

    @property
    def addedScopeEndLine(self):
        """
        End line for the entire scope
        """
        return self.addedScopeStartLine+self.addedScopeEndLine

    def assign(self,data:str)->None:
        """
        assign data to this object
        """
        self.beforeWithContext=ChangeLocation(self,
            ChangeLocationType.FILE_BEFORE_CHANGE|ChangeLocationType.WITH_CONTEXT, # type: ignore
            0)
        self.afterWithContext=ChangeLocation(self,
            ChangeLocationType.FILE_AFTER_CHANGE|ChangeLocationType.WITH_CONTEXT, # type: ignore
            0)
        self.before=[]
        self.after=[]
        beforeLine:int=0
        afterLine:int=0
        gotFirstLine=False
        currentBefore:typing.Optional[ChangeLocation]=None
        currentAfter:typing.Optional[ChangeLocation]=None
        self.differenceType=DifferenceType.TYPE_NONE
        for line in data.split('\n'):
            if not gotFirstLine:
                if line.startswith('@@ '):
                    self.scope=line
                    gotFirstLine=True
                    beforeLine=self.removedScopeStartLine
                    afterLine=self.addedScopeStartLine
                    self.beforeWithContext=ChangeLocation(self,
                        ChangeLocationType.FILE_BEFORE_CHANGE|ChangeLocationType.WITH_CONTEXT, # type: ignore # noqa: E501 # pylint: disable = line-too-long
                        self.removedScopeStartLine)
                    self.afterWithContext=ChangeLocation(self,
                        ChangeLocationType.FILE_AFTER_CHANGE|ChangeLocationType.WITH_CONTEXT, # type: ignore # noqa: E501 # pylint: disable = line-too-long
                        self.addedScopeStartLine)
            else:
                if line.startswith('  '): # common context
                    line=line[2:]
                    self.beforeWithContext.lines.append(line)
                    self.afterWithContext.lines.append(line)
                    currentBefore=None
                    currentAfter=None
                    beforeLine+=1
                    afterLine+=1
                elif line.startswith('+ '): # new/after line
                    line=line[2:]
                    if currentAfter is None:
                        currentAfter=ChangeLocation(self,
                            ChangeLocationType.FILE_AFTER_CHANGE, # type: ignore
                            afterLine)
                        self.differenceType|=DifferenceType.TYPE_ADD # type: ignore
                        self.after.append(currentAfter)
                        currentBefore=None # next before will be a new entry
                    currentAfter.lines.append(line)
                    self.afterWithContext.lines.append(line)
                    afterLine+=1
                elif line.startswith('- '): # old/before line
                    line=line[2:]
                    if currentBefore is None:
                        currentBefore=ChangeLocation(self,
                            ChangeLocationType.FILE_BEFORE_CHANGE, # type: ignore
                            beforeLine)
                        self.differenceType|=DifferenceType.TYPE_REMOVE # type: ignore
                        self.before.append(currentBefore)
                        currentAfter=None # next after will be a new entry
                    currentBefore.lines.append(line)
                    self.beforeWithContext.lines.append(line)
                    beforeLine+=1
                elif line.startswith('@@ '): # next diff
                    break
                else: # blank line
                    self.beforeWithContext.lines.append(line)
                    self.afterWithContext.lines.append(line)
                    currentBefore=None
                    currentAfter=None
                    beforeLine+=1
                    afterLine+=1

    def _lineIter(self,
        inclueDiffMarkers:bool=True
        )->typing.Generator[typing.Tuple[ChangeLocationType,str],None,None]:
        """
        Iterate over all changed lines
        """
        if self.beforeWithContext is None or self.afterWithContext is None:
            return
        if inclueDiffMarkers:
            contextPrefix='  '
            addPrefix='+ '
            removePrefix='- '
        else:
            contextPrefix=''
            addPrefix=''
            removePrefix=''
        beforeListIndex=0
        afterListIndex=0
        oldFileLine=self.removedScopeStartLine
        newFileLine=self.addedScopeStartLine
        while True:
            if beforeListIndex>=len(self.before):
                before=None
                nextOldFileLine=self.beforeWithContext.toLine
            else:
                before=self.before[beforeListIndex]
                nextOldFileLine=before.fromLine
            if afterListIndex>=len(self.after):
                after=None
                nextNewFileLine=self.afterWithContext.toLine
            else:
                after=self.after[afterListIndex]
                nextNewFileLine=after.fromLine
            while oldFileLine<nextOldFileLine and newFileLine<nextNewFileLine:
                yield (
                    ChangeLocationType.WITH_CONTEXT, # type: ignore
                    f'{contextPrefix}{self.beforeWithContext.lines[oldFileLine-self.beforeWithContext.fromLine]}') # noqa: E501 # pylint: disable = line-too-long
                oldFileLine+=1
                newFileLine+=1
            if before is None and after is None:
                break
            if oldFileLine>=nextOldFileLine:
                if before is not None:
                    for line in before.lines:
                        yield (
                            ChangeLocationType.FILE_BEFORE_CHANGE, # type: ignore
                            f'{removePrefix}{line}')
                oldFileLine=nextOldFileLine+1
                beforeListIndex+=1
            if newFileLine>=nextNewFileLine:
                if after is not None:
                    for line in after.lines:
                        yield (
                            ChangeLocationType.FILE_AFTER_CHANGE, # type: ignore
                            f'{addPrefix}{line}')
                newFileLine=nextNewFileLine+1
                afterListIndex+=1
            if newFileLine>self.afterWithContext.toLine \
                or oldFileLine>self.beforeWithContext.toLine:
                break

    def asDiffStr(self,
        colorize:typing.Union[None,typing.Literal['ansi'],typing.Literal['html']]=None,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        if colorize is None:
            return self.asPlainDiffStr(includeDiffMarkers=includeDiffMarkers)
        elif colorize=='html':
            return self.asAnsiDiffStr(includeDiffMarkers=includeDiffMarkers)
        return self.asHtmlDiffStr(includeDiffMarkers=includeDiffMarkers)

    def asAnsiDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with ansi color codes
        """
        from stringTools import ANSI_COLORS
        scope=ANSI_COLORS.ANSI_DARK_CYAN.value
        removed=ANSI_COLORS.ANSI_RED.value
        added=ANSI_COLORS.ANSI_GREEN.value
        off=ANSI_COLORS.ANSI_OFF.value
        ret=[]
        ret.append(f'{scope}{self.scope}{off}')
        for changeLocationType,line in self._lineIter(includeDiffMarkers):
            if changeLocationType&ChangeLocationType.WITH_CONTEXT!=0: # type: ignore
                ret.append(line)
            elif changeLocationType==ChangeLocationType.FILE_BEFORE_CHANGE:
                ret.append(f'{removed}{line}{off}')
            elif changeLocationType==ChangeLocationType.FILE_AFTER_CHANGE:
                ret.append(f'{added}{line}{off}')
        return '\n'.join(ret)

    def asHtmlDiffStr(self,
        scopeColor:str="#77c6ff",
        addColor:str="#00FF00",
        removeColor:str="#FF0000",
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string with html colorization
        """
        ret=[]
        ret.append(f'<div style="color:{scopeColor}">{self.scope}</div>')
        for changeLocationType,line in self._lineIter(includeDiffMarkers):
            if changeLocationType&ChangeLocationType.WITH_CONTEXT!=0: # type: ignore
                ret.append(f'<div">{line}</div>')
            elif changeLocationType==ChangeLocationType.FILE_BEFORE_CHANGE:
                ret.append(f'<div style="color:{removeColor}">{line}</div>')
            elif changeLocationType==ChangeLocationType.FILE_AFTER_CHANGE:
                ret.append(f'<div style="color:{addColor}">{line}</div>')
        return '\n'.join(ret)
    @property
    def html(self)->str:
        """
        Get this as a standard diff string with html colorization
        """
        return self.asHtmlDiffStr()

    def asPlainDiffStr(self,
        includeDiffMarkers:bool=True
        )->str:
        """
        Get this as a standard diff string
        """
        ret=[]
        ret.append(self.scope)
        for _,line in self._lineIter(includeDiffMarkers):
            ret.append(line)
        return '\n'.join(ret)

    @property
    def diffStr(self)->str:
        """
        Get the difference as a string
        """
        return self.asDiffStr()
    @diffStr.setter
    def diffStr(self,diffStr:str):
        self.assign(diffStr)

    @property
    def numLines(self)->int:
        """
        number of lines affected
        """
        beforeLines=0
        for before in self.before:
            beforeLines+=before.numLines
        afterLines=0
        for after in self.after:
            afterLines+=after.numLines
        return max(beforeLines,afterLines)

    @property
    def url(self)->Url:
        """
        The file url
        """
        return self.fileDifferences.url

    def __str__(self)->str:
        return self.asAnsiDiffStr()
