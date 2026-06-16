from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class MarkdownBlockData(BaseModel):
    content: str


class TableBlockData(BaseModel):
    title: Optional[str] = None
    columns: List[str]
    rows: List[List[Union[str, int, float]]]


class ChartDataset(BaseModel):
    label: str
    data: List[float]


class ChartBlockData(BaseModel):
    title: Optional[str] = None
    chart_type: Literal["bar", "line", "pie", "area"]
    labels: List[str]
    datasets: List[ChartDataset]


class UIBlock(BaseModel):
    type: Literal["markdown", "table", "chart"]
    data: Union[MarkdownBlockData, TableBlockData, ChartBlockData, Dict[str, Any]]
