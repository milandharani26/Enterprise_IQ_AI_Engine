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

        response_lines = [f"Found {row_count} record{'s' if row_count > 1 else ''}:"]
        
        # Determine format based on size
        if row_count <= 20:
            # Small dataset: format nicely as a Markdown table
            response_lines.append(f"| {' | '.join(columns)} |")
            response_lines.append(f"|{'---|'*len(columns)}")
            for row in rows:
                vals = [str(row[c]).replace('|', '\\|') for c in columns]
                response_lines.append(f"| {' | '.join(vals)} |")
        else:
            # Large dataset: show first 10 rows only
            response_lines.append(f"(Showing first 10 rows)")
            response_lines.append(f"| {' | '.join(columns)} |")
            response_lines.append(f"|{'---|'*len(columns)}")
            for row in rows[:10]:
                vals = [str(row[c]).replace('|', '\\|') for c in columns]
                response_lines.append(f"| {' | '.join(vals)} |")
            
        return "\n".join(response_lines)
