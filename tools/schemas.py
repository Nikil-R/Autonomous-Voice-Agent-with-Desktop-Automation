"""JSON Schema definitions for Groq / OpenAI function calling."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_vitals",
            "description": "Retrieves real-time system performance metrics including CPU usage %, RAM utilized/free (GB), Drive C free space (GB), and battery percentage.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_processes",
            "description": "Enumerates running Windows processes sorted by memory consumption (RAM) or CPU usage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {
                        "type": "string",
                        "enum": ["memory", "cpu"],
                        "description": "Metric to sort processes by ('memory' or 'cpu'). Default is 'memory'."
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of top processes to return (default 5, max 10)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Recursively searches user directories (Desktop, Downloads, Documents) for files matching optional extension or keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "enum": ["Desktop", "Downloads", "Documents"],
                        "description": "Target user directory to scan."
                    },
                    "extension": {
                        "type": "string",
                        "description": "Optional file extension filter, e.g. '.pdf', '.py', '.txt'."
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Optional keyword substring to match within file names."
                    }
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_local_db",
            "description": "Executes a safe read-only SQL SELECT query against the local SQLite WAL database to inspect system telemetry and audit tables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "A read-only SQL SELECT statement. Example: 'SELECT max(cpu_percent), recorded_at FROM system_telemetry;'"
                    }
                },
                "required": ["sql_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Opens ANY application or desktop software installed on the computer (e.g. WhatsApp, Google Chrome, Spotify, Discord, VS Code, Notepad, Calculator, Terminal, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Application name or software to open (e.g. 'whatsapp', 'chrome', 'spotify', 'notepad', 'calc')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Opens ANY website, web address, social media, or web service directly in a new tab in Google Chrome or default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Website URL or domain (e.g. 'youtube.com', 'wikipedia.org', 'instagram.com', 'facebook.com', 'github.com', 'chatgpt.com', 'reddit.com')."
                    },
                    "browser": {
                        "type": "string",
                        "description": "Browser to target, defaults to 'chrome'."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web_or_play",
            "description": "Performs an instant online search or video play query on YouTube, Google, or Wikipedia in Google Chrome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or video/music title (e.g. 'lofi hip hop', 'quantum computing news', 'Elon Musk')."
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["youtube", "google", "wikipedia"],
                        "description": "Target platform to search on (default 'youtube')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_media_or_volume",
            "description": "Controls desktop system volume, mute, or media playback (play/pause).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["mute", "volume_up", "volume_down", "play_pause", "next", "previous"],
                        "description": "Action to perform on system audio/media."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder_or_path",
            "description": "Locates and opens any user folder, directory, studies folder, or project in Windows File Explorer (e.g. 'Nikhil', 'studies', 'ApexCore', 'Downloads').",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name_or_path": {
                        "type": "string",
                        "description": "Folder name, directory name, or path to open in File Explorer."
                    }
                },
                "required": ["folder_name_or_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desktop_type_or_calculate",
            "description": "Interacts with desktop applications using automated GUI keystrokes. Use when user asks to open Calculator and calculate something (e.g. '20 times 10', '500 plus 250'), or type text into an application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calculation_or_keys": {
                        "type": "string",
                        "description": "Mathematical expression or keystrokes to type (e.g. '20*10', '150+50')."
                    },
                    "app_to_open": {
                        "type": "string",
                        "description": "Optional application to launch first, e.g. 'calculator' or 'calc'."
                    }
                },
                "required": ["calculation_or_keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Brings an open desktop application or window into the absolute foreground and focus (e.g. 'Calculator', 'Chrome', 'Visual Studio Code', 'WhatsApp').",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_or_title": {
                        "type": "string",
                        "description": "Name or title of the window to focus (e.g. 'Calculator', 'Chrome', 'Code')."
                    }
                },
                "required": ["app_or_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_chrome_tab_video",
            "description": "Controls video playback directly inside the open Chrome/YouTube tab using Chrome DevTools Protocol (CDP). Use when user says 'pause the video', 'play the video', 'mute the video', 'unmute', 'forward 10 seconds', or 'rewind'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["pause", "play", "toggle", "mute", "unmute", "forward", "rewind"],
                        "description": "Video playback action to perform inside the Chrome tab."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_chrome_element",
            "description": "Clicks an exact DOM element or top search result inside Google Chrome without guessing coordinates. Use when user says 'click the first search result', 'click the first video', or 'select the top result'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector or 'first_result' to click the top YouTube video or Google search result."
                    }
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fill_chrome_search",
            "description": "Locates the search box in the active Chrome tab (YouTube, Google, Wikipedia) and enters text. Use when user says 'fill in this search box with ...' or 'type ... into Google search'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text query to type into the search box."
                    },
                    "submit": {
                        "type": "boolean",
                        "description": "Whether to press enter and submit search (default true)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_and_analyze_screen",
            "description": "Takes a screenshot of the user's desktop screen and uses Multimodal Vision AI to see, inspect, and describe whatever is on display. Use when user says 'what is on my screen?', 'look at my screen', or asks about visible content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_or_task": {
                        "type": "string",
                        "description": "What to inspect or answer based on the visible screen."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_on_visual_target",
            "description": "Multimodal Screen Grounding: Uses Vision AI to locate the exact (x, y) pixel coordinates of any visible button, icon, link, or object on screen and physically moves the mouse to click it. Use when user says 'click the blue download button', 'select the second song', 'click the submit button', 'click the close icon', or asks to click any visual target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_description": {
                        "type": "string",
                        "description": "Natural language visual description of what to click (e.g. 'blue download button', 'second song in the list', 'search button')."
                    },
                    "double_click": {
                        "type": "boolean",
                        "description": "Whether to perform a double click instead of single click (default false)."
                    }
                },
                "required": ["target_description"]
            }
        }
    }
]
