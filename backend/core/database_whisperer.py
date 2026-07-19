import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("sivi.database_whisperer")

class DatabaseWhisperer:
    """
    Sivi's internal database querying module.
    Allows Sivi to run raw SQL queries directly against local databases to check application state.
    """
    def __init__(self):
        # We cache connections to avoid setting up engines repeatedly
        self.engines = {}

    def _get_engine(self, connection_string: str):
        if connection_string not in self.engines:
            # For sqlite, we need special handling if it's a relative path
            # But we rely on the user passing a valid connection string like "sqlite:///data.db"
            self.engines[connection_string] = create_engine(connection_string)
        return self.engines[connection_string]

    def _is_safe_read_query(self, query: str) -> bool:
        """Simple safety check to prevent accidental DB destruction from Voice/LLM commands."""
        unsafe_keywords = ["drop", "delete", "update", "insert", "alter", "truncate", "grant", "revoke"]
        query_lower = query.lower()
        for kw in unsafe_keywords:
            if kw in query_lower.split():
                return False
        return True

    def execute_read_query(self, connection_string: str, query: str) -> str:
        """
        Executes a SQL SELECT query against the provided connection string.
        Returns a formatted string of the results so Gemini can read it back.
        """
        if not self._is_safe_read_query(query):
            return "SECURITY BLOCK: I refused to run this query because it contains potentially destructive commands like DROP or DELETE. Sivi is configured for read-only SQL."
            
        try:
            engine = self._get_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(text(query))
                
                # Fetch up to 10 rows to prevent blowing up the LLM context window
                rows = result.fetchmany(10)
                
                if not rows:
                    return "The query executed successfully, but returned 0 rows."
                    
                # Format headers and rows
                columns = result.keys()
                formatted_lines = [", ".join(columns)]
                for row in rows:
                    formatted_lines.append(", ".join(str(val) for val in row))
                    
                res_str = "\n".join(formatted_lines)
                if result.rowcount > 10:
                    res_str += "\n... (more rows truncated)"
                    
                return f"Query Results:\n{res_str}"
                
        except SQLAlchemyError as e:
            logger.error(f"Database Whisperer SQL Error: {e}")
            return f"SQL Error: {str(e)}"
        except Exception as e:
            logger.error(f"Database Whisperer General Error: {e}")
            return f"Failed to execute query: {str(e)}"

database_whisperer = DatabaseWhisperer()
