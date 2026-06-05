import pygetwindow as gw

class WindowReader:
    def get_active_windows(self) -> str:
        try:
            titles = gw.getAllTitles()
            # Filter out empty or common hidden system window names
            active = [t for t in titles if t.strip() and t not in ["Program Manager", "Settings", "Microsoft Text Input Application"]]
            if not active:
                return "No visible applications are currently open."
            
            return "Currently open applications/windows:\n- " + "\n- ".join(active[:15]) # Limit to 15
        except Exception as e:
            return f"Failed to read active windows: {e}"

window_reader = WindowReader()
