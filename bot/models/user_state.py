"""
Модели состояний пользователей
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class UserState:
    """Состояние пользователя"""
    state: str
    data: Dict[str, Any]
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DangerReportData:
    """Данные сообщения об опасности"""
    description: str
    location: str
    media_files: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.media_files is None:
            self.media_files = []


@dataclass
class ShelterData:
    """Данные убежища"""
    id: int
    name: str
    lat: float
    lon: float
    photo_path: str
    map_link: str
    description: str


@dataclass
class DocumentData:
    """Данные документа"""
    id: int
    title: str
    description: str
    file_path: str
    category: str


@dataclass
class IncidentData:
    """Данные инцидента"""
    timestamp: str
    user_id: int
    username: Optional[str]
    description: str
    location: str
    media_files: List[Dict[str, Any]]
