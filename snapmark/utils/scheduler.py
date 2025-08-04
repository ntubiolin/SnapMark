import schedule
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable, Optional

from ..core.markdown_generator import MarkdownGenerator
from ..core.ai_summary import AISummaryGenerator


class TaskScheduler:
    def __init__(self, md_gen: MarkdownGenerator, ai_gen: Optional[AISummaryGenerator] = None):
        self.md_gen = md_gen
        self.ai_gen = ai_gen
        self.running = False
        self.thread = None
    
    def setup_daily_summary(self, time_str: str = "18:00"):
        if self.ai_gen:
            schedule.every().day.at(time_str).do(self._generate_daily_summary)
    
    def setup_weekly_summary(self, day: str = "sunday", time_str: str = "19:00"):
        if self.ai_gen:
            getattr(schedule.every(), day.lower()).at(time_str).do(self._generate_weekly_summary)
    
    def _generate_daily_summary(self):
        try:
            yesterday = datetime.now() - timedelta(days=1)
            notes = self.md_gen.get_daily_notes(yesterday)
            
            if not notes:
                return
            
            note_contents = []
            for note_path in notes:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                note_contents.append(content)
            
            summary = self.ai_gen.generate_daily_summary(note_contents, yesterday)
            
            # Create summary markdown file
            summary_path = note_path.parent / f"daily_summary_{yesterday.strftime('%Y-%m-%d')}.md"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Daily Summary - {yesterday.strftime('%Y-%m-%d')}\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(summary)
                f.write(f"\n\n## Source Notes ({len(notes)} files)\n\n")
                for note in notes:
                    f.write(f"- {note.name}\n")
            
        except Exception as e:
            print(f"Error generating daily summary: {e}")
    
    def _generate_weekly_summary(self):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            all_notes = []
            current_date = start_date
            
            while current_date <= end_date:
                daily_notes = self.md_gen.get_daily_notes(current_date)
                all_notes.extend(daily_notes)
                current_date += timedelta(days=1)
            
            if not all_notes:
                return
            
            note_contents = []
            for note_path in all_notes:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                note_contents.append(content)
            
            summary = self.ai_gen.generate_daily_summary(note_contents, end_date)
            
            # Create weekly summary
            week_path = self.md_gen.output_dir / "weekly_summaries"
            week_path.mkdir(exist_ok=True)
            
            summary_path = week_path / f"weekly_summary_{end_date.strftime('%Y-W%U')}.md"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Weekly Summary - Week {end_date.strftime('%U, %Y')}\n\n")
                f.write(f"**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(summary)
                f.write(f"\n\n## Source Notes ({len(all_notes)} files)\n\n")
                for note in all_notes:
                    f.write(f"- {note.name}\n")
            
        except Exception as e:
            print(f"Error generating weekly summary: {e}")
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
    
    def stop(self):
        self.running = False
        schedule.clear()
    
    def _run_scheduler(self):
        while self.running:
            schedule.run_pending()
            time.sleep(60)