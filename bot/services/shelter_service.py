"""
Сервис для работы с убежищами
"""
from typing import List, Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.interfaces import IFileManager, ILogger
from bot.models.user_state import ShelterData


class ShelterService:
    """Сервис для работы с убежищами"""
    
    def __init__(self, file_manager: IFileManager, logger: ILogger):
        self.file_manager = file_manager
        self.logger = logger
    
    def get_shelters(self) -> List[ShelterData]:
        """Получить список убежищ"""
        data = self.file_manager.load_json('configs/data_placeholders.json')
        shelters_data = data.get('shelters', [])
        
        shelters = []
        for shelter_data in shelters_data:
            shelter = ShelterData(
                id=shelter_data['id'],
                name=shelter_data['name'],
                lat=shelter_data['lat'],
                lon=shelter_data['lon'],
                photo_path=shelter_data['photo_path'],
                map_link=shelter_data['map_link'],
                description=shelter_data['description']
            )
            shelters.append(shelter)
        
        return shelters
    
    def get_nearby_shelters(self, user_lat: float, user_lon: float, radius_km: float = 1.0) -> List[ShelterData]:
        """Получить ближайшие убежища (заглушка - возвращает все)"""
        # В реальной версии здесь будет расчет расстояния
        return self.get_shelters()[:3]  # Возвращаем первые 3
    
    async def send_shelter_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              shelter: ShelterData) -> None:
        """Отправить информацию об убежище"""
        text = f"🏠 **{shelter.name}**\n\n"
        text += f"{shelter.description}\n\n"
        text += f"📍 Координаты: {shelter.lat}, {shelter.lon}"
        
        # Отправляем изображение убежища (заглушка)
        try:
            with open(shelter.photo_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=text,
                    parse_mode='Markdown'
                )
        except FileNotFoundError:
            # Если файл не найден, отправляем только текст
            await update.message.reply_text(
                text,
                parse_mode='Markdown'
            )
    
    def get_shelter_map_link(self, shelter: ShelterData) -> str:
        """Получить ссылку на карту убежища"""
        return shelter.map_link
