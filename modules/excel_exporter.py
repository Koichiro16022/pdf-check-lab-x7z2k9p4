# modules/excel_exporter.py
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.comments import Comment
from datetime import datetime
from io import BytesIO
import copy


class ExcelExporter:

    def __init__(self):
        self.wb = None
        self.yellow_fill = PatternFill(
            start_color="FFFF00",
            end_color="FFFF00",
            fill_type="solid"
        )
        self.gray_fill = PatternFill(
            start_color="D3D3D3",
            end_color="D3D3D3",
            fill_type="solid"
        )
        self.orange_fill = PatternFill(
            start_color="FFA500",
            end_color="FFA500",
            fill_type="solid"
        )
        self.red_font = Font(color="FF0000", bold=True)
        self.white_font = Font(color="FFFFFF", bold=True)

    def _write_cell_value(self, new_cell, source_cell):
        """セルの値を書き込む（MergedCellはスキップ）"""
        from openpyxl.cell.cell import MergedCell
        if isinstance(source_cell, MergedCell):
            return  # 結合セルの子セルは読み取り専用のためスキップ

        val = source_cell.value

        if val is None:
            new_cell.value = None
            return

        if isinstance(val, str):
            new_cell.number_format = '@'
            new_cell.value = val
        else:
            new_cell.value = val

    def create_report_simple(
        self, ws_check, cell_diffs, hidden_diffs, image_diffs, setting_diffs=None
    ):
        self.wb = Workbook()
        self._create_summary_sheet(
            cell_diffs, hidden_diffs, image_diffs, mode="simple"
        )
        self._create_detail_sheet(cell_diffs, hidden_diffs, image_diffs)
        self._create_result_sheet_simple(
            ws_check, cell_diffs, hidden_diffs, image_diffs
        )
        if setting_diffs:
            self._create_settings_diff_sheet(setting_diffs)
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        return output.getvalue()

    def create_report_formatted(
        self, ws_check, cell_diffs, hidden_diffs, image_diffs, setting_diffs=None
    ):
        self.wb = Workbook()
        self._create_summary_sheet(
            cell_diffs, hidden_diffs, image_diffs, mode="formatted"
        )
        self._create_detail_sheet(cell_diffs, hidden_diffs, image_diffs)
        self._create_result_sheet_with_format(
            ws_check, cell_diffs, hidden_diffs, image_diffs
        )
        if setting_diffs:
            self._create_settings_diff_sheet(setting_diffs)
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _create_summary_sheet(
        self, cell_diffs, hidden_diffs, image_diffs, mode="simple"
    ):
        ws = self.wb.active
        ws.title = "サマリー"
        mode_text = "書式保持版" if mode == "formatted" else "書式無視版"
        ws['A1'] = f"零(ZERO) 検証結果レポート（{mode_text}）"
        ws['A1'].font = Font(size=16, bold=True)
        ws['A2'] = f"作成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}"
        ws['A2'].font = Font(size=10, italic=True)

        row = 4
        ws[f'A{row}'] = "【検証結果サマリー】"
        ws[f'A{row}'].font = Font(size=12, bold=True)

        row += 1
        ws[f'A{row}'] = "不一致セル数:"
        ws[f'B{row}'] = len(cell_diffs)
        ws[f'B{row}'].font = Font(color="FF0000", bold=True)

        row += 1
        ws[f'A{row}'] = "非表示セル差異:"
        ws[f'B{row}'] = len(hidden_diffs)
        ws[f'B{row}'].font = Font(color="FFA500", bold=True)

        row += 1
        ws[f'A{row}'] = "画像差異:"
        ws[f'B{row}'] = len(image_diffs)
        ws[f'B{row}'].font = Font(color="0000FF", bold=True)

        row += 1
        ws[f'A{row}'] = "合計:"
        ws[f'B{row}'] = len(cell_diffs) + len(hidden_diffs) + len(image_diffs)
        ws[f'B{row}'].font = Font(size=12, bold=True)

        row += 2
        ws[f'A{row}'] = "【差異の種類別内訳】"
        ws[f'A{row}'].font = Font(size=12, bold=True)

        diff_types = {}
        for diff in cell_diffs + hidden_diffs:
            for d in diff['differences']:
                dtype = d['type']
                diff_types[dtype] = diff_types.get(dtype, 0) + 1

        row += 1
        ws[f'A{row}'] = "種類"
        ws[f'B{row}'] = "件数"
        ws[f'A{row}'].font = Font(bold=True)
        ws[f'B{row}'].font = Font(bold=True)

        for dtype, count in sorted(
            diff_types.items(), key=lambda x: x[1], reverse=True
        ):
            row += 1
            ws[f'A{row}'] = dtype
            ws[f'B{row}'] = count

        row += 3
        ws[f'A{row}'] = "【シート構成】"
        ws[f'A{row}'].font = Font(size=12, bold=True)

        row += 1
        ws[f'A{row}'] = "Sheet1: サマリー"
        ws[f'B{row}'] = "検証結果の概要"

        row += 1
        ws[f'A{row}'] = "Sheet2: 不一致詳細リスト"
        ws[f'B{row}'] = "差異の一覧（フィルター機能付き）"

        row += 1
        ws[f'A{row}'] = "Sheet3: 比較結果"
        ws[f'B{row}'] = (
            f"{'書式保持' if mode == 'formatted' else '書式無視'}・色付き結果"
        )
        ws[f'B{row}'].font = Font(color="0000FF", bold=True)

        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 30

    def _create_result_sheet_simple(
        self, ws_check, cell_diffs, hidden_diffs, image_diffs
    ):
        ws = self.wb.create_sheet("比較結果")
        diff_positions = {diff['position']: diff for diff in cell_diffs}
        hidden_positions = {diff['position']: diff for diff in hidden_diffs}

        from openpyxl.cell.cell import MergedCell
        for row in ws_check.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue  # 結合セルの子セルはスキップ
                new_cell = ws.cell(row=cell.row, column=cell.column)
                self._write_cell_value(new_cell, cell)

                if cell.has_style:
                    new_cell.font = copy.copy(cell.font)
                    new_cell.border = copy.copy(cell.border)
                    new_cell.protection = copy.copy(cell.protection)
                    new_cell.alignment = copy.copy(cell.alignment)
                    new_cell.number_format = cell.number_format

                position = cell.coordinate

                if position in diff_positions:
                    new_cell.fill = self.yellow_fill
                    new_cell.font = self.red_font
                    diff = diff_positions[position]
                    comment_text = self._create_comment_text(diff)
                    new_cell.comment = Comment(comment_text, "零(ZERO)")
                    new_cell.comment.width = 450
                    new_cell.comment.height = 500

                elif position in hidden_positions:
                    new_cell.fill = self.orange_fill
                    new_cell.font = self.white_font
                    diff = hidden_positions[position]
                    comment_text = (
                        "🟠 非表示セルの差異\n\n"
                        + self._create_comment_text(diff)
                    )
                    new_cell.comment = Comment(comment_text, "零(ZERO)")
                    new_cell.comment.width = 450
                    new_cell.comment.height = 500

                else:
                    new_cell.fill = self.gray_fill

        for img_diff in image_diffs:
            if img_diff.get('position') and \
               img_diff['position'] not in ['全体', '不明']:
                try:
                    cell = ws[img_diff['position']]
                    cell.fill = self.yellow_fill
                    cell.comment = Comment(
                        f"🖼️ 画像の差異\n\n{img_diff['detail']}",
                        "零(ZERO)"
                    )
                except:
                    pass

    def _create_result_sheet_with_format(
        self, ws_check, cell_diffs, hidden_diffs, image_diffs
    ):
        ws = self.wb.create_sheet("比較結果")
        diff_positions = {diff['position']: diff for diff in cell_diffs}
        hidden_positions = {diff['position']: diff for diff in hidden_diffs}

        for merged_range in ws_check.merged_cells.ranges:
            ws.merge_cells(str(merged_range))

        for col_letter, col_dim in ws_check.column_dimensions.items():
            ws.column_dimensions[col_letter].width = col_dim.width
            ws.column_dimensions[col_letter].hidden = col_dim.hidden

        for row_num, row_dim in ws_check.row_dimensions.items():
            ws.row_dimensions[row_num].height = row_dim.height
            ws.row_dimensions[row_num].hidden = row_dim.hidden

        from openpyxl.cell.cell import MergedCell
        for row in ws_check.iter_rows():
            for cell in row:
                if isinstance(cell, MergedCell):
                    continue  # ソース側の結合子セルはスキップ
                new_cell = ws.cell(row=cell.row, column=cell.column)
                if isinstance(new_cell, MergedCell):
                    continue  # ターゲット側の結合子セルもスキップ
                self._write_cell_value(new_cell, cell)

                if cell.has_style:
                    new_cell.font = copy.copy(cell.font)
                    new_cell.border = copy.copy(cell.border)
                    new_cell.protection = copy.copy(cell.protection)
                    new_cell.alignment = copy.copy(cell.alignment)
                    new_cell.fill = copy.copy(cell.fill)
                    new_cell.number_format = cell.number_format

                position = cell.coordinate

                if position in diff_positions:
                    new_cell.fill = self.yellow_fill
                    original_font = (
                        copy.copy(cell.font) if cell.font else Font()
                    )
                    new_cell.font = Font(
                        name=original_font.name,
                        size=original_font.size,
                        bold=True,
                        italic=original_font.italic,
                        underline=original_font.underline,
                        color="FF0000"
                    )
                    diff = diff_positions[position]
                    comment_text = self._create_comment_text(diff)
                    new_cell.comment = Comment(comment_text, "零(ZERO)")
                    new_cell.comment.width = 450
                    new_cell.comment.height = 500

                elif position in hidden_positions:
                    new_cell.fill = self.orange_fill
                    original_font = (
                        copy.copy(cell.font) if cell.font else Font()
                    )
                    new_cell.font = Font(
                        name=original_font.name,
                        size=original_font.size,
                        bold=True,
                        italic=original_font.italic,
                        underline=original_font.underline,
                        color="FFFFFF"
                    )
                    diff = hidden_positions[position]
                    comment_text = (
                        "🟠 非表示セルの差異\n\n"
                        + self._create_comment_text(diff)
                    )
                    new_cell.comment = Comment(comment_text, "零(ZERO)")
                    new_cell.comment.width = 450
                    new_cell.comment.height = 500

                else:
                    new_cell.fill = self.gray_fill

        self._copy_shapes(ws_check, ws)

        for img_diff in image_diffs:
            if img_diff.get('position') and \
               img_diff['position'] not in ['全体', '不明']:
                try:
                    cell = ws[img_diff['position']]
                    cell.fill = self.yellow_fill
                    cell.comment = Comment(
                        f"🖼️ 画像の差異\n\n{img_diff['detail']}",
                        "零(ZERO)"
                    )
                except:
                    pass

    def _copy_shapes(self, ws_source, ws_target):
        try:
            if hasattr(ws_source, '_shapes'):
                for shape in ws_source._shapes:
                    try:
                        new_shape = copy.deepcopy(shape)
                        ws_target._shapes.append(new_shape)
                    except:
                        pass
        except:
            pass

    def _create_detail_sheet(self, cell_diffs, hidden_diffs, image_diffs):
        ws = self.wb.create_sheet("不一致詳細リスト")

        headers = [
            'No.', 'セル位置', '種類', '差異タイプ', '原本', '比較データ', '詳細'
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(1, col, header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", fill_type="solid")

        row = 2

        for i, diff in enumerate(cell_diffs, 1):
            for d in diff['differences']:
                ws.cell(row, 1, i)
                ws.cell(row, 2, diff['position'])
                ws.cell(row, 3, "🟡 セル差異")
                ws.cell(row, 4, d['type'])
                master_cell = ws.cell(
                    row, 5, str(d.get('master', ''))[:100]
                )
                check_cell = ws.cell(
                    row, 6, str(d.get('check', ''))[:100]
                )
                master_cell.number_format = '@'
                check_cell.number_format = '@'
                ws.cell(row, 7, d['detail'])
                row += 1

        for i, diff in enumerate(hidden_diffs, 1):
            for d in diff['differences']:
                ws.cell(row, 1, len(cell_diffs) + i)
                ws.cell(row, 2, diff['position'])
                ws.cell(row, 3, "🟠 非表示差異")
                ws.cell(row, 4, d['type'])
                master_cell = ws.cell(
                    row, 5, str(d.get('master', ''))[:100]
                )
                check_cell = ws.cell(
                    row, 6, str(d.get('check', ''))[:100]
                )
                master_cell.number_format = '@'
                check_cell.number_format = '@'
                ws.cell(row, 7, d['detail'])
                row += 1

        for i, img_diff in enumerate(image_diffs, 1):
            ws.cell(row, 1, len(cell_diffs) + len(hidden_diffs) + i)
            ws.cell(row, 2, img_diff.get('position', '不明'))
            ws.cell(row, 3, "🖼️ 画像差異")
            ws.cell(row, 4, img_diff['type'])
            ws.cell(row, 5, str(img_diff.get('master', '')))
            ws.cell(row, 6, str(img_diff.get('check', '')))
            ws.cell(row, 7, img_diff['detail'])
            row += 1

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 30
        ws.column_dimensions['G'].width = 40

        if row > 1:
            ws.auto_filter.ref = f"A1:G{row-1}"

    def _create_comment_text(self, diff):
        circle_nums = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']
        lines = ["🔍 差異の詳細"]

        has_space_only = False
        num_idx = 0

        for d in diff['differences']:
            master_val = str(d.get('master', ''))
            check_val = str(d.get('check', ''))
            num = circle_nums[num_idx] if num_idx < len(circle_nums) else f"({num_idx + 1})"
            num_idx += 1

            if d['type'] == 'value':
                master_display = master_val[:50] + ('（数式）' if master_val.startswith('=') else '')
                check_display = check_val[:50] + ('（数式）' if check_val.startswith('=') else '')
            elif d['type'] == 'number_format':
                import re
                mv = d.get('master_value')
                cv = d.get('check_value')

                def _fmt_num(value, fmt):
                    from datetime import datetime, date as date_type
                    if value is None:
                        return ''
                    # 日付・日時型の処理
                    if isinstance(value, (datetime, date_type)):
                        # openpyxlの組み込み日付コード→日本語表示へ変換
                        builtin_map = {
                            'mm-dd-yy': 'yyyy/m/d',
                            'd-mmm-yy': 'yyyy/m/d',
                            'd-mmm': 'm/d',
                            'mmm-yy': 'yyyy/m',
                            'm/d/yy': 'yyyy/m/d',
                            'm/d/yy h:mm': 'yyyy/m/d',
                        }
                        f = builtin_map.get(fmt.lower(), fmt.lower())
                        # yyyy/yy/mm/m/dd/d の順に置換（長いものから先に）
                        f = f.replace('yyyy', str(value.year))
                        f = f.replace('yy', str(value.year)[-2:])
                        f = f.replace('mm', f"{value.month:02d}")
                        f = f.replace('m', str(value.month))
                        f = f.replace('dd', f"{value.day:02d}")
                        f = f.replace('d', str(value.day))
                        # 時刻部分は除去
                        f = re.sub(r'\s*h+:mm(:ss)?', '', f).strip()
                        return f
                    # 数値型の処理
                    if not isinstance(value, (int, float)):
                        return str(value)
                    m = re.search(r'\.([0#]+)', fmt)
                    decimals = len(m.group(1)) if m else 0
                    use_comma = ',' in fmt
                    try:
                        if use_comma:
                            return f"{value:,.{decimals}f}"
                        else:
                            return f"{value:.{decimals}f}"
                    except Exception:
                        return str(value)

                master_display = _fmt_num(mv, master_val) if mv is not None else master_val
                check_display = _fmt_num(cv, check_val) if cv is not None else check_val
                # detail の表示も実際の値に差し替え
                detail = f"表示形式が違う: {master_display} -> {check_display}"
                if ': ' in detail:
                    detail_label, detail_value = detail.split(': ', 1)
                    lines.append(f"{num}{detail_label}:")
                    lines.append(f" {detail_value}")
                else:
                    lines.append(f"{num}{detail}")
                lines.append(f" 原本: {master_display}")
                lines.append(f" 比較データ: {check_display}")
                continue
            elif d['type'] == 'data_type':
                mv = d.get('master_value', '')
                cv = d.get('check_value', '')
                type_short = {
                    '数値型': '数値', '文字列型': '文字', '数式型': '数式',
                    '論理値型': '論理値', '日付型': '日付',
                    'エラー型': 'エラー', '不明': '不明'
                }
                reading_hints = {
                    '0': '（ゼロ）', 'O': '（オー）', 'o': '（オー）',
                    '1': '（イチ）', 'l': '（エル）', 'I': '（アイ）'
                }
                m_short = type_short.get(master_val, master_val)
                c_short = type_short.get(check_val, check_val)
                # スペース文字を可視化してから reading_hints を適用
                from datetime import datetime, date as _dt
                def _vis_val(v):
                    if v is None or v == '':
                        return ''
                    if isinstance(v, (datetime, _dt)):
                        return f"{v.year}/{v.month}/{v.day}"
                    return str(v).replace('　', '（全角スペース）').replace(' ', '（半角スペース）')
                mv_vis = _vis_val(mv)
                cv_vis = _vis_val(cv)
                m_hint = reading_hints.get(mv_vis, '')
                c_hint = reading_hints.get(cv_vis, '')
                master_display = f"{m_short}の　{mv_vis}{m_hint}" if mv else master_val
                check_display = f"{c_short}の　{cv_vis}{c_hint}" if cv else check_val
            else:
                master_display = master_val[:50]
                check_display = check_val[:50]

            detail = d['detail']
            if ': ' in detail:
                detail_label, detail_value = detail.split(': ', 1)
                lines.append(f"{num}{detail_label}:")
                lines.append(f" {detail_value}")
            else:
                lines.append(f"{num}{detail}")
            lines.append(f" 原本: {master_display}")
            lines.append(f" 比較データ: {check_display}")

            # スペースのみセルのチェック（ラベルを除いた残りが空の場合のみ）
            def _is_space_only(v):
                cleaned = v
                for lbl in ['（半角スペース）', '（全角スペース）',
                             '（特殊スペース・半角幅）', '（特殊スペース・全角幅）',
                             '（見えないスペース）']:
                    cleaned = cleaned.replace(lbl, '')
                return cleaned == '' and v not in ('', '(空白セル)', '(空文字)')
            if _is_space_only(master_val) or _is_space_only(check_val):
                has_space_only = True

        rec_num = circle_nums[num_idx] if num_idx < len(circle_nums) else f"({num_idx + 1})"
        lines.append(f"{rec_num}推奨アクション: 目視で内容を確認してください")

        if has_space_only:
            lines.append("⚠️ 注意: （半角スペース）のみのセルはExcelの仕様上、セル内には表示されません。差異はこのコメントで確認してください。")

        return "\n".join(lines)

    def _create_settings_diff_sheet(self, setting_diffs):
        """シート・ブック設定の差異を別シートに出力"""
        ws = self.wb.create_sheet(title="設定差異")

        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True, size=11)
        category_fill = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
        diff_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

        from openpyxl.styles import Alignment, Border, Side
        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        ws['A1'] = "シート・ブック設定 差異レポート"
        ws['A1'].font = Font(size=14, bold=True, color="1F4E79")
        ws.merge_cells('A1:E1')

        ws['A2'] = f"生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
        ws['A2'].font = Font(size=9, color="666666")
        ws.merge_cells('A2:E2')

        ws['A3'] = f"検出件数: {len(setting_diffs)} 件"
        ws['A3'].font = Font(size=10, bold=True)
        ws.merge_cells('A3:E3')

        headers = ["No.", "カテゴリ", "項目", "原本", "比較"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = border

        if setting_diffs:
            for row_idx, diff in enumerate(setting_diffs, 6):
                no_cell = ws.cell(row=row_idx, column=1, value=row_idx - 5)
                no_cell.alignment = Alignment(horizontal='center', vertical='center')
                no_cell.border = border

                cat_cell = ws.cell(row=row_idx, column=2, value=diff.get('category', ''))
                cat_cell.fill = category_fill
                cat_cell.alignment = Alignment(horizontal='center', vertical='center')
                cat_cell.border = border

                item_cell = ws.cell(row=row_idx, column=3, value=diff.get('detail', diff.get('type', '')))
                item_cell.alignment = Alignment(vertical='center', wrap_text=True)
                item_cell.border = border

                master_cell = ws.cell(row=row_idx, column=4, value=str(diff.get('master', '')))
                master_cell.alignment = Alignment(vertical='center', wrap_text=True)
                master_cell.border = border

                check_cell = ws.cell(row=row_idx, column=5, value=str(diff.get('check', '')))
                check_cell.fill = diff_fill
                check_cell.alignment = Alignment(vertical='center', wrap_text=True)
                check_cell.border = border

        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 25

        if setting_diffs:
            ws.auto_filter.ref = f"A5:E{5 + len(setting_diffs)}"