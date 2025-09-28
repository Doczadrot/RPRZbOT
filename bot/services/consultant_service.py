"""
Сервис для консультанта по безопасности
"""
from typing import List, Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.interfaces import IFileManager, ILogger
from bot.models.user_state import DocumentData


class ConsultantService:
    """Сервис для консультанта по безопасности"""
    
    def __init__(self, file_manager: IFileManager, logger: ILogger):
        self.file_manager = file_manager
        self.logger = logger
    
    def get_documents(self) -> List[DocumentData]:
        """Получить список документов"""
        data = self.file_manager.load_json('configs/data_placeholders.json')
        documents_data = data.get('documents', [])
        
        documents = []
        for doc_data in documents_data:
            document = DocumentData(
                id=doc_data['id'],
                title=doc_data['title'],
                description=doc_data['description'],
                file_path=doc_data['file_path'],
                category=doc_data.get('category', 'unknown')
            )
            documents.append(document)
        
        return documents
    
    def get_document_by_id(self, doc_id: int) -> Optional[DocumentData]:
        """Получить документ по ID"""
        documents = self.get_documents()
        for doc in documents:
            if doc.id == doc_id:
                return doc
        return None
    
    def get_document_by_index(self, index: int) -> Optional[DocumentData]:
        """Получить документ по индексу (0-based)"""
        documents = self.get_documents()
        if 0 <= index < len(documents):
            return documents[index]
        return None
    
    async def send_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          document: DocumentData) -> None:
        """Отправить документ пользователю"""
        try:
            with open(document.file_path, 'rb') as pdf_file:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"{document.title}.pdf",
                    caption=f"📄 **{document.title}**\n\n{document.description}"
                )
        except FileNotFoundError:
            await update.message.reply_text(
                f"❌ Файл документа '{document.title}' не найден."
            )
    
    def get_answer_template(self, question: str) -> dict:
        """Получить шаблон ответа на вопрос"""
        data = self.file_manager.load_json('configs/data_placeholders.json')
        responses = data.get('suggestions_responses', {})
        
        return {
            'answer': responses.get('default_answer', 'Заглушка-ответ по вашему вопросу.'),
            'source': responses.get('default_source', 'Документ №X, стр. Y, п. Z (заглушка).'),
            'detailed': responses.get('detailed_responses', {}).get('safety', 'Подробная информация не найдена.')
        }
    
    def log_question(self, user_id: int, username: Optional[str], question: str) -> None:
        """Логировать заданный вопрос"""
        self.logger.log_activity(
            user_id,
            username,
            "question_asked",
            question[:50]
        )
