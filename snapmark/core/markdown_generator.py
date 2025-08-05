import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class MarkdownGenerator:
    def __init__(self, output_dir: str = "SnapMarkData"):
        self.output_dir = Path(output_dir)
    
    def create_markdown_note(
        self, 
        image_path: str, 
        ocr_text: str, 
        vlm_description: Optional[str] = None,
        tags: Optional[list] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        image_path = Path(image_path)
        timestamp = datetime.now()
        
        if not title:
            title = f"Screenshot {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        md_filename = image_path.stem + ".md"
        md_filepath = image_path.parent / md_filename
        
        content = self._generate_markdown_content(
            title=title,
            timestamp=timestamp,
            image_path=image_path,
            ocr_text=ocr_text,
            vlm_description=vlm_description,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(md_filepath)
    
    def _generate_markdown_content(
        self,
        title: str,
        timestamp: datetime,
        image_path: Path,
        ocr_text: str,
        vlm_description: Optional[str],
        tags: list,
        metadata: Dict[str, Any]
    ) -> str:
        content = f"""# {title}

**Created:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Image:** {image_path.name}
"""
        
        if tags:
            tag_str = " ".join([f"#{tag}" for tag in tags])
            content += f"**Tags:** {tag_str}\n"
        
        if metadata:
            content += "\n## Metadata\n\n"
            for key, value in metadata.items():
                content += f"- **{key.title()}:** {value}\n"
        
        content += f"\n## Screenshot\n\n![Screenshot]({image_path.name})\n"
        
        if vlm_description and vlm_description.strip():
            content += f"\n## Image Description (VLM)\n\n{vlm_description}\n"
        
        if ocr_text and ocr_text.strip():
            content += f"\n## OCR Text\n\n```\n{ocr_text}\n```\n"
        
        content += "\n## Notes\n\n<!-- Add your notes here -->\n"
        
        return content
    
    def update_note_with_summary(self, md_filepath: str, summary: str):
        with open(md_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "## AI Summary" not in content:
            summary_section = f"\n## AI Summary\n\n{summary}\n"
            content = content.replace("## Notes", f"{summary_section}\n## Notes")
            
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def get_daily_notes(self, date: Optional[datetime] = None) -> list:
        if not date:
            date = datetime.now()
        
        date_path = self.output_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        
        if not date_path.exists():
            return []
        
        return list(date_path.glob("*.md"))