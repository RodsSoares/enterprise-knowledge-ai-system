from app.ingestion.schemas import (
    ChartBlock,
    ChartSourceReference,
    ContentBlock,
    ImageBlock,
    SpreadsheetBlock,
    SpreadsheetCell,
    TableBlock,
    TextBlock,
)


class BlockSerializer:
    """Creates deterministic textual representations of canonical blocks."""

    def serialize(self, block: ContentBlock) -> str | None:
        if isinstance(block, TextBlock):
            return block.text

        if isinstance(block, TableBlock):
            return self._serialize_table(block)

        if isinstance(block, SpreadsheetBlock):
            return self._serialize_spreadsheet(block)

        if isinstance(block, ChartBlock):
            return self._serialize_chart(block)

        if isinstance(block, ImageBlock):
            return block.caption

        return None

    @staticmethod
    def _serialize_table(block: TableBlock) -> str:
        lines: list[str] = []

        if block.caption is not None:
            lines.append(f"Caption: {block.caption}")

        if block.headers:
            lines.append(" | ".join(block.headers))

        lines.extend(
            " | ".join(
                "" if value is None else str(value)
                for value in row
            )
            for row in block.rows
        )

        return "\n".join(lines)

    @classmethod
    def _serialize_spreadsheet(
        cls,
        block: SpreadsheetBlock,
    ) -> str:
        lines = [f"Sheet: {block.sheet_name}"]

        if block.cell_range is not None:
            lines.append(f"Range: {block.cell_range}")

        if block.table_name is not None:
            lines.append(f"Table: {block.table_name}")

        lines.extend(
            cls._serialize_spreadsheet_cell(cell)
            for cell in block.cells
        )

        return "\n".join(lines)

    @staticmethod
    def _serialize_spreadsheet_cell(
        cell: SpreadsheetCell,
    ) -> str:
        if cell.value is not None and cell.formula is not None:
            return (
                f"{cell.coordinate} = {cell.value} "
                f"[formula: {cell.formula}]"
            )

        if cell.formula is not None:
            return f"{cell.coordinate} [formula: {cell.formula}]"

        if cell.value is not None:
            return f"{cell.coordinate} = {cell.value}"

        return f"{cell.coordinate} ="

    @classmethod
    def _serialize_chart(
        cls,
        block: ChartBlock,
    ) -> str:
        lines: list[str] = []

        if block.title is not None:
            lines.append(f"Chart: {block.title}")

        lines.append(f"Type: {block.chart_type}")

        if block.categories:
            lines.append(
                "Categories: "
                + cls._join_values(block.categories)
            )

        if block.category_source_reference is not None:
            lines.append(
                "Category source: "
                + cls._serialize_chart_source_reference(
                    block.category_source_reference
                )
            )

        for series in block.series:
            if series.name is not None:
                lines.append(f"Series: {series.name}")
            else:
                lines.append("Series:")

            if series.values:
                lines.append(
                    "Values: "
                    + cls._join_values(series.values)
                )
            else:
                lines.append("Values:")

            if series.source_reference is not None:
                lines.append(
                    "Source: "
                    + cls._serialize_chart_source_reference(
                        series.source_reference
                    )
                )

        return "\n".join(lines)

    @staticmethod
    def _serialize_chart_source_reference(
        reference: ChartSourceReference,
    ) -> str:
        values = (
            reference.resource,
            reference.sheet_name,
            reference.cell_range,
            reference.status,
        )

        return " | ".join(
            "" if value is None else str(value)
            for value in values
        )

    @staticmethod
    def _join_values(
        values: tuple[str | int | float | bool | None, ...],
    ) -> str:
        return " | ".join(
            "" if value is None else str(value)
            for value in values
        )
