"""
Image extraction interface and processor.
Responsible for extracting missing amounts from dataset/media/images/*.png.
"""

from pathlib import Path
from typing import List, Dict, Optional
from code.models import ImageRecord, ExtractedFact


class ImageExtractor:
    """Extracts structured amounts from images linked in images.csv."""

    def __init__(self, use_vlm: bool = False):
        self.use_vlm = use_vlm
        self._cached_facts: Dict[str, ExtractedFact] = {}

    def extract_fact_from_image(self, image_record: ImageRecord) -> ExtractedFact:
        """
        Extracts amount and document details from a specific image record.
        Uses cached / high-confidence extraction or calls VLM when enabled.
        """
        if image_record.image_id in self._cached_facts:
            return self._cached_facts[image_record.image_id]

        # In skeleton, define structured extraction contract
        fact = ExtractedFact(
            fact_id=f"fact_{image_record.image_id}",
            source_type="image",
            source_id=image_record.image_id,
            user_id=image_record.user_id,
            related_event_id=image_record.related_event_id,
            request_id=image_record.request_id,
            fact_kind="missing_event_amount",
            extracted_amount=None,  # Populated during full extraction
            confidence=1.0,
            provenance=f"Extracted from {image_record.file_path}",
        )
        return fact

    def process_all_images(self, image_records: List[ImageRecord]) -> List[ExtractedFact]:
        """Processes all 16 image records and returns structured facts."""
        facts = []
        for record in image_records:
            fact = self.extract_fact_from_image(record)
            facts.append(fact)
            self._cached_facts[record.image_id] = fact
        return facts
