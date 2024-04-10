from dataclasses import dataclass
from typing import Optional
from libs.structs.struct import Struct
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class CrawlerPostStruct(Struct):
    """crawler post struct"""
    account: str = ''
    site: str = ''
    content: str = ''
    timestamp: str = ''
    urls: str = ''
    media: str = ''
    media_ocr: str = ''
    account: str = ''
    is_reply: bool = False
    self_reply: bool = False
    account_id: int = 0
    reply_to: Optional[int] = None
    remote_id: Optional[int] = None
    pre_score: Optional[Decimal] = None
    score: Optional[Decimal] = None
    replies:  Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    replies: Optional[int] = None
    followers: Optional[int] = None
    post_id: Optional[int] = None

    def calculate_pre_score(self):
        base_score = (self.followers * Decimal(0.001) if self.followers else 0)+ \
                     (self.views * Decimal(0.01) if self.views else 0) + \
                     (self.replies * Decimal(2) if self.replies else 0) + \
                     (self.reposts * Decimal(5) if self.reposts else 0) + \
                     (self.likes * Decimal(3) if self.likes else 0) + \
                     (len(self.content) * Decimal(0.05))
        if self.is_reply:
            base_score *= Decimal(0.8)
        if self.self_reply:
            base_score *= Decimal(1.1)
        if self.media:
            base_score *= Decimal(1.2)
        self.pre_score = base_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
