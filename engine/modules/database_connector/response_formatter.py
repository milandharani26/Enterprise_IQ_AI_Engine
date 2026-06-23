from typing import List, Dict, Any

class SqlResponseFormatter:
    @staticmethod
    def format_response(question: str, columns: List[str], rows: List[Dict[str, Any]], row_count: int) -> str:
        """
        Formats raw SQL results into a human-readable summary block for the LLM 
        or for direct UI consumption.
        """
        if row_count == 0:
            return "No results found for your query."

        # Filter out sensitive columns and truncate cell values to prevent token bloat
        exclude_cols = {"password", "refresh_token", "access_token", "token", "secret", "auth_token"}
        filtered_columns = [c for c in columns if c.lower() not in exclude_cols]

        if not filtered_columns:
            return f"Found {row_count} records, but all columns were filtered as sensitive."

        response_lines = [f"Found {row_count} record{'s' if row_count > 1 else ''}:"]
        
        def format_row_value(val: Any) -> str:
            val_str = str(val if val is not None else "")
            if len(val_str) > 100:
                val_str = val_str[:97] + "..."
            return val_str.replace('|', '\\|')

        # Determine format based on size
        if row_count <= 20:
            # Small dataset: format nicely as a Markdown table
            response_lines.append(f"| {' | '.join(filtered_columns)} |")
            response_lines.append(f"|{'---|'*len(filtered_columns)}")
            for row in rows:
                vals = [format_row_value(row[c]) for c in filtered_columns]
                response_lines.append(f"| {' | '.join(vals)} |")
        else:
            # Large dataset: show first 10 rows only
            response_lines.append(f"(Showing first 10 rows)")
            response_lines.append(f"| {' | '.join(filtered_columns)} |")
            response_lines.append(f"|{'---|'*len(filtered_columns)}")
            for row in rows[:10]:
                vals = [format_row_value(row[c]) for c in filtered_columns]
                response_lines.append(f"| {' | '.join(vals)} |")
            
        return "\n".join(response_lines)
