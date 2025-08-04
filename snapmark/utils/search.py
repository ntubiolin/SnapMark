import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sqlite3


class SearchEngine:
    def __init__(self, data_dir: str = "SnapMarkData"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "search_index.db"
        self.data_dir.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                filepath TEXT,
                title TEXT,
                content TEXT,
                ocr_text TEXT,
                tags TEXT,
                created_date TEXT,
                modified_date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_content ON notes(content)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_ocr_text ON notes(ocr_text)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tags ON notes(tags)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_date ON notes(created_date)
        ''')
        
        conn.commit()
        conn.close()
    
    def index_note(self, md_filepath: str):
        md_path = Path(md_filepath)
        if not md_path.exists():
            return
        
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata from markdown
        title = self._extract_title(content)
        ocr_text = self._extract_ocr_text(content)
        tags = self._extract_tags(content)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO notes 
            (filename, filepath, title, content, ocr_text, tags, created_date, modified_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            md_path.name,
            str(md_path),
            title,
            content,
            ocr_text,
            ','.join(tags),
            datetime.fromtimestamp(md_path.stat().st_ctime).isoformat(),
            datetime.fromtimestamp(md_path.stat().st_mtime).isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def search(
        self, 
        query: str, 
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM notes WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (content LIKE ? OR ocr_text LIKE ? OR title LIKE ?)"
            query_param = f"%{query}%"
            params.extend([query_param, query_param, query_param])
        
        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        if date_from:
            sql += " AND created_date >= ?"
            params.append(date_from.isoformat())
        
        if date_to:
            sql += " AND created_date <= ?"
            params.append(date_to.isoformat())
        
        sql += " ORDER BY modified_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return results
    
    def get_all_tags(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT tags FROM notes WHERE tags != ''")
        rows = cursor.fetchall()
        
        all_tags = set()
        for row in rows:
            if row[0]:
                tags = row[0].split(',')
                all_tags.update(tag.strip() for tag in tags if tag.strip())
        
        conn.close()
        return sorted(list(all_tags))
    
    def rebuild_index(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes")
        conn.commit()
        conn.close()
        
        # Re-index all markdown files
        for md_file in self.data_dir.rglob("*.md"):
            if not md_file.name.startswith("daily_summary_") and not md_file.name.startswith("weekly_summary_"):
                self.index_note(str(md_file))
    
    def _extract_title(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"
    
    def _extract_ocr_text(self, content: str) -> str:
        ocr_match = re.search(r'## OCR Text\s*\n\s*```\s*\n(.*?)\n```', content, re.DOTALL)
        return ocr_match.group(1).strip() if ocr_match else ""
    
    def _extract_tags(self, content: str) -> List[str]:
        tag_match = re.search(r'\*\*Tags:\*\*\s*(.+)', content)
        if tag_match:
            tag_text = tag_match.group(1)
            tags = re.findall(r'#(\w+)', tag_text)
            return tags
        return []


class FileManager:
    def __init__(self, data_dir: str = "SnapMarkData"):
        self.data_dir = Path(data_dir)
    
    def get_daily_files(self, date: datetime) -> List[Path]:
        date_path = self.data_dir / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"
        if date_path.exists():
            return list(date_path.glob("*.md"))
        return []
    
    def get_recent_files(self, days: int = 7) -> List[Path]:
        files = []
        current_date = datetime.now()
        
        for i in range(days):
            date = current_date - timedelta(days=i)
            daily_files = self.get_daily_files(date)
            files.extend(daily_files)
        
        return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def delete_file_pair(self, md_path: Path) -> bool:
        try:
            img_path = md_path.with_suffix('.png')
            
            if md_path.exists():
                md_path.unlink()
            
            if img_path.exists():
                img_path.unlink()
            
            return True
        except Exception:
            return False
    
    def get_storage_stats(self) -> Dict[str, int]:
        total_files = 0
        total_size = 0
        
        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "markdown_files": len(list(self.data_dir.rglob("*.md"))),
            "image_files": len(list(self.data_dir.rglob("*.png")))
        }