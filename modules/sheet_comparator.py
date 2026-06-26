# modules/sheet_comparator.py
"""シート・ブック設定の比較モジュール"""


class SheetComparator:
    """シートおよびブックレベルの設定差異を比較するクラス"""

    def compare_books(self, wb_master, wb_check, sheet_name_master, sheet_name_check):
        """
        ブック・シートレベルの設定差異を比較する

        Returns:
            list: 差異の一覧
                  各要素: {'category': str, 'item': str, 'master': str, 'check': str, 'detail': str}
        """
        diffs = []

        # ブックレベル比較
        diffs.extend(self._compare_defined_names(wb_master, wb_check))
        diffs.extend(self._compare_calculation(wb_master, wb_check))
        diffs.extend(self._compare_sheet_states(wb_master, wb_check))
        diffs.extend(self._compare_book_properties(wb_master, wb_check))

        # シートレベル比較
        ws_m = None
        ws_c = None
        try:
            if sheet_name_master in wb_master.sheetnames:
                ws_m = wb_master[sheet_name_master]
        except Exception:
            pass
        try:
            if sheet_name_check in wb_check.sheetnames:
                ws_c = wb_check[sheet_name_check]
        except Exception:
            pass

        # ブックレベル追加
        diffs.extend(self._compare_sheet_names_and_order(wb_master, wb_check))
        diffs.extend(self._compare_workbook_protection(wb_master, wb_check))

        if ws_m and ws_c:
            diffs.extend(self._compare_sheet_view(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_tab_color(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_sheet_protection(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_auto_filter(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_freeze_panes(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_grouping(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_show_headers(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_show_sheet_tabs(wb_master, wb_check))
            diffs.extend(self._compare_defined_name_scope(wb_master, wb_check))
            diffs.extend(self._compare_page_setup(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_print_options(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_header_footer(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_page_breaks(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_column_row_dimensions(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_conditional_formatting(ws_m, ws_c, sheet_name_master))
            diffs.extend(self._compare_data_validations(ws_m, ws_c, sheet_name_master))

        return diffs

    # ------------------------------------------------------------------
    # No.93: 名前の定義
    # ------------------------------------------------------------------
    def _compare_defined_names(self, wb_m, wb_c):
        diffs = []
        try:
            def get_names(wb):
                result = {}
                try:
                    for name, defn in wb.defined_names.items():
                        result[name] = str(defn.attr_text) if defn.attr_text else ''
                except Exception:
                    try:
                        for defn in wb.defined_names.definedName:
                            result[defn.name] = str(defn.attr_text) if defn.attr_text else ''
                    except Exception:
                        pass
                return result

            names_m = get_names(wb_m)
            names_c = get_names(wb_c)
            all_names = sorted(set(list(names_m.keys()) + list(names_c.keys())))

            for name in all_names:
                val_m = names_m.get(name)
                val_c = names_c.get(name)
                if val_m != val_c:
                    diffs.append({
                        'category': 'ブック設定',
                        'item': f'名前の定義: {name}',
                        'master': val_m if val_m is not None else '(なし)',
                        'check': val_c if val_c is not None else '(なし)',
                        'detail': f'名前の定義「{name}」が違う'
                    })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.96: R1C1参照形式 / No.128: 反復計算
    # ------------------------------------------------------------------
    def _compare_calculation(self, wb_m, wb_c):
        diffs = []
        try:
            calc_m = getattr(wb_m, 'calculation', None)
            calc_c = getattr(wb_c, 'calculation', None)

            # 反復計算 (No.128)
            iter_m = bool(getattr(calc_m, 'iterate', False)) if calc_m else False
            iter_c = bool(getattr(calc_c, 'iterate', False)) if calc_c else False
            if iter_m != iter_c:
                diffs.append({
                    'category': 'ブック設定',
                    'item': '反復計算',
                    'master': '有効' if iter_m else '無効',
                    'check': '有効' if iter_c else '無効',
                    'detail': '反復計算の設定が違う'
                })

            # 計算方法 (No.95相当 - 自動/手動)
            mode_labels = {
                'auto': '自動',
                'manual': '手動',
                'autoNoTable': '自動(テーブル除く)'
            }
            mode_m = getattr(calc_m, 'calcMode', 'auto') if calc_m else 'auto'
            mode_c = getattr(calc_c, 'calcMode', 'auto') if calc_c else 'auto'
            if mode_m != mode_c:
                diffs.append({
                    'category': 'ブック設定',
                    'item': '計算方法',
                    'master': mode_labels.get(mode_m, str(mode_m)),
                    'check': mode_labels.get(mode_c, str(mode_c)),
                    'detail': '計算方法の設定が違う'
                })

        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.125: 非表示シートの再表示
    # ------------------------------------------------------------------
    def _compare_sheet_states(self, wb_m, wb_c):
        diffs = []
        try:
            state_labels = {
                'visible': '表示',
                'hidden': '非表示',
                'veryHidden': '完全非表示'
            }
            states_m = {}
            for name in wb_m.sheetnames:
                try:
                    states_m[name] = wb_m[name].sheet_state
                except Exception:
                    states_m[name] = 'visible'

            states_c = {}
            for name in wb_c.sheetnames:
                try:
                    states_c[name] = wb_c[name].sheet_state
                except Exception:
                    states_c[name] = 'visible'

            all_sheets = sorted(set(list(states_m.keys()) + list(states_c.keys())))
            for name in all_sheets:
                st_m = states_m.get(name)
                st_c = states_c.get(name)
                if st_m != st_c:
                    diffs.append({
                        'category': 'シート設定',
                        'item': f'シート表示状態: {name}',
                        'master': state_labels.get(st_m, str(st_m)) if st_m else '(シートなし)',
                        'check': state_labels.get(st_c, str(st_c)) if st_c else '(シートなし)',
                        'detail': f'シート「{name}」の表示状態が違う'
                    })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.117: ゼロ値の表示設定
    # ------------------------------------------------------------------
    def _compare_sheet_view(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_show_zeros(ws):
                try:
                    sv = ws.sheet_view
                    val = getattr(sv, 'showZeros', None)
                    if val is None:
                        return True
                    return bool(val)
                except Exception:
                    return True

            sz_m = get_show_zeros(ws_m)
            sz_c = get_show_zeros(ws_c)
            if sz_m != sz_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'ゼロ値の表示: {sheet_name}',
                    'master': '表示する' if sz_m else '非表示',
                    'check': '表示する' if sz_c else '非表示',
                    'detail': 'ゼロ値の表示設定が違う'
                })

            # No.90: 目盛線の表示
            def get_show_gridlines(ws):
                try:
                    val = getattr(ws.sheet_view, 'showGridLines', None)
                    return True if val is None else bool(val)
                except Exception:
                    return True

            gl_m = get_show_gridlines(ws_m)
            gl_c = get_show_gridlines(ws_c)
            if gl_m != gl_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'目盛線の表示: {sheet_name}',
                    'master': '表示' if gl_m else '非表示',
                    'check': '表示' if gl_c else '非表示',
                    'detail': '目盛線の表示設定が違う'
                })

            # No.89: ズーム倍率
            def get_zoom(ws):
                try:
                    val = getattr(ws.sheet_view, 'zoomScale', None)
                    return int(val) if val is not None else 100
                except Exception:
                    return 100

            zm_m = get_zoom(ws_m)
            zm_c = get_zoom(ws_c)
            if zm_m != zm_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'ズーム倍率: {sheet_name}',
                    'master': f'{zm_m}%',
                    'check': f'{zm_c}%',
                    'detail': 'ズーム倍率が違う'
                })

        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.130: シート見出し（タブ色）
    # ------------------------------------------------------------------
    def _compare_tab_color(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_tab_color(ws):
                try:
                    props = getattr(ws, 'sheet_properties', None)
                    if not props:
                        return None
                    tc = getattr(props, 'tabColor', None)
                    if tc is None:
                        return None
                    color_type = getattr(tc, 'type', None)
                    if color_type == 'theme':
                        theme = getattr(tc, 'theme', None)
                        tint = getattr(tc, 'tint', 0) or 0
                        return f'テーマ色{theme}(tint={tint:.2f})'
                    rgb_val = getattr(tc, 'rgb', None)
                    if rgb_val and isinstance(rgb_val, str) and len(rgb_val) == 8:
                        return f'RGB:{rgb_val}'
                    indexed = getattr(tc, 'indexed', None)
                    if isinstance(indexed, int):
                        return f'インデックス色{indexed}'
                    return '(設定あり)'
                except Exception:
                    return None

            color_m = get_tab_color(ws_m)
            color_c = get_tab_color(ws_c)
            if color_m != color_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'シート見出し色: {sheet_name}',
                    'master': color_m or '(なし)',
                    'check': color_c or '(なし)',
                    'detail': 'シート見出し（タブ）の色が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.74: シート名の不一致 / No.75: シートの並び順違い
    # ------------------------------------------------------------------
    def _compare_sheet_names_and_order(self, wb_m, wb_c):
        diffs = []
        try:
            names_m = wb_m.sheetnames
            names_c = wb_c.sheetnames
            set_m = set(names_m)
            set_c = set(names_c)

            only_m = sorted(set_m - set_c)
            only_c = sorted(set_c - set_m)
            if only_m or only_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': 'シート名の不一致',
                    'master': ', '.join(only_m) if only_m else '(なし)',
                    'check': ', '.join(only_c) if only_c else '(なし)',
                    'detail': f'原本のみ: {only_m}  比較のみ: {only_c}'
                })

            order_m = [n for n in names_m if n in set_c]
            order_c = [n for n in names_c if n in set_m]
            if order_m != order_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': 'シートの並び順',
                    'master': ' > '.join(order_m),
                    'check': ' > '.join(order_c),
                    'detail': 'シートの並び順が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.76: シートの保護状態
    # ------------------------------------------------------------------
    def _compare_sheet_protection(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_protection(ws):
                p = getattr(ws, 'protection', None)
                if p is None:
                    return False
                return bool(getattr(p, 'sheet', False))

            pm = get_protection(ws_m)
            pc = get_protection(ws_c)
            if pm != pc:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'シートの保護: {sheet_name}',
                    'master': '保護あり' if pm else '保護なし',
                    'check': '保護あり' if pc else '保護なし',
                    'detail': 'シートの保護設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.77: ブックの保護状態
    # ------------------------------------------------------------------
    def _compare_workbook_protection(self, wb_m, wb_c):
        diffs = []
        try:
            def get_wb_protection(wb):
                sec = getattr(wb, 'security', None)
                if sec is None:
                    return False
                return bool(getattr(sec, 'workbookPassword', None) or
                            getattr(sec, 'lockStructure', False) or
                            getattr(sec, 'lockWindows', False))

            pm = get_wb_protection(wb_m)
            pc = get_wb_protection(wb_c)
            if pm != pc:
                diffs.append({
                    'category': 'ブック設定',
                    'item': 'ブックの保護状態',
                    'master': '保護あり' if pm else '保護なし',
                    'check': '保護あり' if pc else '保護なし',
                    'detail': 'ブックの保護設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.47: オートフィルタのオン・オフ
    # ------------------------------------------------------------------
    def _compare_auto_filter(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_filter(ws):
                af = getattr(ws, 'auto_filter', None)
                if af is None:
                    return None
                ref = getattr(af, 'ref', None)
                return str(ref) if ref else None

            af_m = get_filter(ws_m)
            af_c = get_filter(ws_c)
            if af_m != af_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'オートフィルタ: {sheet_name}',
                    'master': af_m or '(なし)',
                    'check': af_c or '(なし)',
                    'detail': 'オートフィルタの設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.49: ウィンドウ枠の固定
    # ------------------------------------------------------------------
    def _compare_freeze_panes(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            fp_m = getattr(ws_m, 'freeze_panes', None)
            fp_c = getattr(ws_c, 'freeze_panes', None)
            if fp_m == 'A1':
                fp_m = None
            if fp_c == 'A1':
                fp_c = None
            if fp_m != fp_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'ウィンドウ枠の固定: {sheet_name}',
                    'master': str(fp_m) if fp_m else '(なし)',
                    'check': str(fp_c) if fp_c else '(なし)',
                    'detail': 'ウィンドウ枠固定の設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.114: グループ化（アウトライン）
    # ------------------------------------------------------------------
    def _compare_grouping(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_outline(ws):
                row_groups = {}
                for r, rd in ws.row_dimensions.items():
                    lvl = getattr(rd, 'outlineLevel', 0) or 0
                    if lvl > 0:
                        row_groups[r] = lvl
                col_groups = {}
                for c, cd in ws.column_dimensions.items():
                    lvl = getattr(cd, 'outlineLevel', 0) or 0
                    if lvl > 0:
                        col_groups[c] = lvl
                return row_groups, col_groups

            rg_m, cg_m = get_outline(ws_m)
            rg_c, cg_c = get_outline(ws_c)

            if rg_m != rg_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'行グループ化: {sheet_name}',
                    'master': str(rg_m) if rg_m else '(なし)',
                    'check': str(rg_c) if rg_c else '(なし)',
                    'detail': '行のグループ化（アウトライン）が違う'
                })
            if cg_m != cg_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'列グループ化: {sheet_name}',
                    'master': str(cg_m) if cg_m else '(なし)',
                    'check': str(cg_c) if cg_c else '(なし)',
                    'detail': '列のグループ化（アウトライン）が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.122: 行列番号（見出し）の非表示
    # ------------------------------------------------------------------
    def _compare_show_headers(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_show_headers(ws):
                try:
                    sv = ws.sheet_view
                    val = getattr(sv, 'showRowColHeaders', None)
                    return True if val is None else bool(val)
                except Exception:
                    return True

            sh_m = get_show_headers(ws_m)
            sh_c = get_show_headers(ws_c)
            if sh_m != sh_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'行列番号の表示: {sheet_name}',
                    'master': '表示' if sh_m else '非表示',
                    'check': '表示' if sh_c else '非表示',
                    'detail': '行列番号（見出し）の表示設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.129: シート見出し（タブ）の非表示
    # ------------------------------------------------------------------
    def _compare_show_sheet_tabs(self, wb_m, wb_c):
        diffs = []
        try:
            def get_show_tabs(wb):
                try:
                    views = getattr(wb, 'views', None)
                    if views and len(views) > 0:
                        val = getattr(views[0], 'showSheetTabs', None)
                        return True if val is None else bool(val)
                except Exception:
                    pass
                return True

            tm = get_show_tabs(wb_m)
            tc = get_show_tabs(wb_c)
            if tm != tc:
                diffs.append({
                    'category': 'ブック設定',
                    'item': 'シート見出し（タブ）の表示',
                    'master': '表示' if tm else '非表示',
                    'check': '表示' if tc else '非表示',
                    'detail': 'シート見出し（タブ）の表示設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.118: 名前の定義のスコープ（ブック vs シート）
    # ------------------------------------------------------------------
    def _compare_defined_name_scope(self, wb_m, wb_c):
        diffs = []
        try:
            def get_scopes(wb):
                result = {}
                try:
                    for name, defn in wb.defined_names.items():
                        scope = getattr(defn, 'localSheetId', None)
                        result[name] = scope
                except Exception:
                    try:
                        for defn in wb.defined_names.definedName:
                            scope = getattr(defn, 'localSheetId', None)
                            result[defn.name] = scope
                    except Exception:
                        pass
                return result

            scopes_m = get_scopes(wb_m)
            scopes_c = get_scopes(wb_c)
            all_names = sorted(set(list(scopes_m.keys()) + list(scopes_c.keys())))
            for name in all_names:
                sm = scopes_m.get(name)
                sc = scopes_c.get(name)
                if sm != sc:
                    def label(s):
                        return 'ブックスコープ' if s is None else f'シートスコープ(index={s})'
                    diffs.append({
                        'category': 'ブック設定',
                        'item': f'名前のスコープ: {name}',
                        'master': label(sm) if name in scopes_m else '(なし)',
                        'check': label(sc) if name in scopes_c else '(なし)',
                        'detail': f'名前「{name}」のスコープが違う'
                    })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.78/79/80/81/82/86/87: ページセットアップ
    # ------------------------------------------------------------------
    def _compare_page_setup(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_margins(ws):
                m = getattr(ws, 'page_margins', None)
                if m is None:
                    return None
                return {
                    'left': round(getattr(m, 'left', 0) or 0, 4),
                    'right': round(getattr(m, 'right', 0) or 0, 4),
                    'top': round(getattr(m, 'top', 0) or 0, 4),
                    'bottom': round(getattr(m, 'bottom', 0) or 0, 4),
                    'header': round(getattr(m, 'header', 0) or 0, 4),
                    'footer': round(getattr(m, 'footer', 0) or 0, 4),
                }

            mg_m = get_margins(ws_m)
            mg_c = get_margins(ws_c)
            if mg_m != mg_c and (mg_m is not None or mg_c is not None):
                diffs.append({
                    'category': 'シート設定',
                    'item': f'ページ余白: {sheet_name}',
                    'master': str(mg_m) if mg_m else '(デフォルト)',
                    'check': str(mg_c) if mg_c else '(デフォルト)',
                    'detail': 'ページ余白の設定が違う'
                })

            ps_m = getattr(ws_m, 'page_setup', None)
            ps_c = getattr(ws_c, 'page_setup', None)

            paper_labels = {
                1: 'Letter', 5: 'Legal', 8: 'A3', 9: 'A4', 10: 'A4 Small',
                11: 'A5', 13: 'B4', 14: 'B5', None: '(デフォルト/A4)'
            }

            paper_m = getattr(ps_m, 'paperSize', None) if ps_m else None
            paper_c = getattr(ps_c, 'paperSize', None) if ps_c else None
            if paper_m != paper_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'用紙サイズ: {sheet_name}',
                    'master': paper_labels.get(paper_m, str(paper_m)),
                    'check': paper_labels.get(paper_c, str(paper_c)),
                    'detail': '用紙サイズの設定が違う'
                })

            orient_m = getattr(ps_m, 'orientation', None) if ps_m else None
            orient_c = getattr(ps_c, 'orientation', None) if ps_c else None
            if orient_m != orient_c:
                labels = {'portrait': '縦', 'landscape': '横', None: '(デフォルト/縦)'}
                diffs.append({
                    'category': 'シート設定',
                    'item': f'印刷向き: {sheet_name}',
                    'master': labels.get(orient_m, str(orient_m)),
                    'check': labels.get(orient_c, str(orient_c)),
                    'detail': '印刷向きの設定が違う'
                })

            scale_m = getattr(ps_m, 'scale', None) if ps_m else None
            scale_c = getattr(ps_c, 'scale', None) if ps_c else None
            if scale_m != scale_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'拡大縮小印刷: {sheet_name}',
                    'master': f'{scale_m}%' if scale_m is not None else '(100%)',
                    'check': f'{scale_c}%' if scale_c is not None else '(100%)',
                    'detail': '拡大縮小印刷の設定が違う'
                })

            ftp_m = bool(getattr(ps_m, 'fitToPage', False)) if ps_m else False
            ftp_c = bool(getattr(ps_c, 'fitToPage', False)) if ps_c else False
            if ftp_m != ftp_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'1ページに印刷: {sheet_name}',
                    'master': '有効' if ftp_m else '無効',
                    'check': '有効' if ftp_c else '無効',
                    'detail': '1ページに印刷設定が違う'
                })

            ptr_m = getattr(ws_m, 'print_title_rows', None)
            ptr_c = getattr(ws_c, 'print_title_rows', None)
            if ptr_m != ptr_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'タイトル行: {sheet_name}',
                    'master': str(ptr_m) if ptr_m else '(なし)',
                    'check': str(ptr_c) if ptr_c else '(なし)',
                    'detail': 'タイトル行の設定が違う'
                })

            ptc_m = getattr(ws_m, 'print_title_cols', None)
            ptc_c = getattr(ws_c, 'print_title_cols', None)
            if ptc_m != ptc_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'タイトル列: {sheet_name}',
                    'master': str(ptc_m) if ptc_m else '(なし)',
                    'check': str(ptc_c) if ptc_c else '(なし)',
                    'detail': 'タイトル列の設定が違う'
                })

        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.88/89: 印刷オプション（枠線・白黒）
    # ------------------------------------------------------------------
    def _compare_print_options(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            po_m = getattr(ws_m, 'print_options', None)
            po_c = getattr(ws_c, 'print_options', None)

            gl_m = bool(getattr(po_m, 'gridLines', False)) if po_m else False
            gl_c = bool(getattr(po_c, 'gridLines', False)) if po_c else False
            if gl_m != gl_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'枠線の印刷: {sheet_name}',
                    'master': '印刷する' if gl_m else '印刷しない',
                    'check': '印刷する' if gl_c else '印刷しない',
                    'detail': '枠線の印刷設定が違う'
                })

            ps_m = getattr(ws_m, 'page_setup', None)
            ps_c = getattr(ws_c, 'page_setup', None)
            bw_m = bool(getattr(ps_m, 'blackAndWhite', False)) if ps_m else False
            bw_c = bool(getattr(ps_c, 'blackAndWhite', False)) if ps_c else False
            if bw_m != bw_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'白黒印刷: {sheet_name}',
                    'master': '有効' if bw_m else '無効',
                    'check': '有効' if bw_c else '無効',
                    'detail': '白黒印刷の設定が違う'
                })

            # No.84: 印刷範囲
            pa_m = getattr(ws_m, 'print_area', None) or ''
            pa_c = getattr(ws_c, 'print_area', None) or ''
            # シート名プレフィックスを除去して比較
            def strip_sheet_prefix(pa):
                if pa and '!' in pa:
                    return pa.split('!', 1)[1]
                return pa
            pa_m_clean = strip_sheet_prefix(pa_m)
            pa_c_clean = strip_sheet_prefix(pa_c)
            if pa_m_clean != pa_c_clean:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'印刷範囲: {sheet_name}',
                    'master': pa_m_clean if pa_m_clean else '(なし)',
                    'check': pa_c_clean if pa_c_clean else '(なし)',
                    'detail': '印刷範囲の設定が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.84/85: ヘッダー・フッター
    # ------------------------------------------------------------------
    def _compare_header_footer(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_hf(ws):
                result = {}
                oh = getattr(ws, 'oddHeader', None)
                of_ = getattr(ws, 'oddFooter', None)
                result['odd_header'] = (str(getattr(oh, 'left', '') or '') + '|' +
                                        str(getattr(oh, 'center', '') or '') + '|' +
                                        str(getattr(oh, 'right', '') or '')) if oh else ''
                result['odd_footer'] = (str(getattr(of_, 'left', '') or '') + '|' +
                                        str(getattr(of_, 'center', '') or '') + '|' +
                                        str(getattr(of_, 'right', '') or '')) if of_ else ''
                return result

            hf_m = get_hf(ws_m)
            hf_c = get_hf(ws_c)

            if hf_m.get('odd_header') != hf_c.get('odd_header'):
                diffs.append({
                    'category': 'シート設定',
                    'item': f'ヘッダー: {sheet_name}',
                    'master': hf_m.get('odd_header') or '(なし)',
                    'check': hf_c.get('odd_header') or '(なし)',
                    'detail': 'ヘッダーの内容が違う'
                })

            if hf_m.get('odd_footer') != hf_c.get('odd_footer'):
                diffs.append({
                    'category': 'シート設定',
                    'item': f'フッター: {sheet_name}',
                    'master': hf_m.get('odd_footer') or '(なし)',
                    'check': hf_c.get('odd_footer') or '(なし)',
                    'detail': 'フッターの内容が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.83: 改ページ
    # ------------------------------------------------------------------
    def _compare_page_breaks(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_breaks(ws):
                rb = set()
                cb = set()
                try:
                    for brk in ws.row_breaks.brk:
                        rb.add(brk.id)
                except Exception:
                    pass
                try:
                    for brk in ws.col_breaks.brk:
                        cb.add(brk.id)
                except Exception:
                    pass
                return sorted(rb), sorted(cb)

            rb_m, cb_m = get_breaks(ws_m)
            rb_c, cb_c = get_breaks(ws_c)

            if rb_m != rb_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'行の改ページ: {sheet_name}',
                    'master': str(rb_m) if rb_m else '(なし)',
                    'check': str(rb_c) if rb_c else '(なし)',
                    'detail': '行の改ページ位置が違う'
                })
            if cb_m != cb_c:
                diffs.append({
                    'category': 'シート設定',
                    'item': f'列の改ページ: {sheet_name}',
                    'master': str(cb_m) if cb_m else '(なし)',
                    'check': str(cb_c) if cb_c else '(なし)',
                    'detail': '列の改ページ位置が違う'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.41/42: 列幅・行高さ
    # ------------------------------------------------------------------
    def _compare_column_row_dimensions(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_col_widths(ws):
                result = {}
                for col, cd in ws.column_dimensions.items():
                    w = getattr(cd, 'width', None)
                    if w is not None:
                        result[col] = round(float(w), 4)
                return result

            cw_m = get_col_widths(ws_m)
            cw_c = get_col_widths(ws_c)
            all_cols = sorted(set(list(cw_m.keys()) + list(cw_c.keys())))
            col_diffs = []
            for col in all_cols:
                wm = cw_m.get(col)
                wc = cw_c.get(col)
                if wm != wc:
                    col_diffs.append(f'{col}({wm}->{wc})')
            if col_diffs:
                summary = ', '.join(col_diffs[:10])
                if len(col_diffs) > 10:
                    summary += f' ...他{len(col_diffs)-10}列'
                diffs.append({
                    'category': 'シート設定',
                    'item': f'列幅の違い: {sheet_name}',
                    'master': f'{len(col_diffs)}列が異なる',
                    'check': summary,
                    'detail': f'列幅が異なる列: {summary}'
                })

            def get_row_heights(ws):
                result = {}
                for row, rd in ws.row_dimensions.items():
                    h = getattr(rd, 'height', None)
                    if h is not None:
                        result[row] = round(float(h), 4)
                return result

            rh_m = get_row_heights(ws_m)
            rh_c = get_row_heights(ws_c)
            all_rows = sorted(set(list(rh_m.keys()) + list(rh_c.keys())))
            row_diffs = []
            for row in all_rows:
                hm = rh_m.get(row)
                hc = rh_c.get(row)
                if hm != hc:
                    row_diffs.append(f'行{row}({hm}->{hc})')
            if row_diffs:
                summary = ', '.join(row_diffs[:10])
                if len(row_diffs) > 10:
                    summary += f' ...他{len(row_diffs)-10}行'
                diffs.append({
                    'category': 'シート設定',
                    'item': f'行高さの違い: {sheet_name}',
                    'master': f'{len(row_diffs)}行が異なる',
                    'check': summary,
                    'detail': f'行高さが異なる行: {summary}'
                })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.51–57: 条件付き書式の比較
    # ------------------------------------------------------------------
    def _compare_conditional_formatting(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_cf_summary(ws):
                result = {}
                cf = getattr(ws, 'conditional_formatting', None)
                if cf is None:
                    return result
                try:
                    cf_list = cf._cf_rules
                    for sqref, rules in cf_list.items():
                        key = str(sqref)
                        rule_strs = []
                        for rule in rules:
                            parts = [
                                f"type={getattr(rule, 'type', '?')}",
                                f"operator={getattr(rule, 'operator', '')}",
                                f"formula={getattr(rule, 'formula', '')}",
                                f"priority={getattr(rule, 'priority', '')}",
                                f"stopIfTrue={getattr(rule, 'stopIfTrue', False)}",
                            ]
                            rule_strs.append('|'.join(str(p) for p in parts))
                        result[key] = sorted(rule_strs)
                except Exception:
                    try:
                        for sqref in cf:
                            rules = cf[sqref]
                            key = str(sqref)
                            result[key] = sorted([str(r) for r in rules])
                    except Exception:
                        pass
                return result

            cf_m = get_cf_summary(ws_m)
            cf_c = get_cf_summary(ws_c)
            all_ranges = sorted(set(list(cf_m.keys()) + list(cf_c.keys())))

            for rng in all_ranges:
                rules_m = cf_m.get(rng)
                rules_c = cf_c.get(rng)
                if rules_m != rules_c:
                    diffs.append({
                        'category': 'シート設定',
                        'item': f'条件付き書式: {sheet_name} [{rng}]',
                        'master': str(rules_m) if rules_m is not None else '(なし)',
                        'check': str(rules_c) if rules_c is not None else '(なし)',
                        'detail': f'条件付き書式のルールが違う (範囲: {rng})'
                    })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.58–62 / No.112 / No.120: データの入力規則の比較
    # ------------------------------------------------------------------
    def _compare_data_validations(self, ws_m, ws_c, sheet_name):
        diffs = []
        try:
            def get_dv_summary(ws):
                result = {}
                dvs = getattr(ws, 'data_validations', None)
                if dvs is None:
                    return result
                # openpyxl 3.x: 直接イテレーション、失敗時はdataValidation属性
                try:
                    dv_list = list(dvs)
                except Exception:
                    dv_list = getattr(dvs, 'dataValidation', [])
                for dv in dv_list:
                    key = str(getattr(dv, 'sqref', ''))
                    result[key] = {
                        'type': getattr(dv, 'type', None),
                        'operator': getattr(dv, 'operator', None),
                        'formula1': str(getattr(dv, 'formula1', '') or ''),
                        'formula2': str(getattr(dv, 'formula2', '') or ''),
                        'showDropDown': getattr(dv, 'showDropDown', None),
                        'allow_blank': getattr(dv, 'allow_blank', None),
                        'error': str(getattr(dv, 'error', '') or ''),
                        'errorTitle': str(getattr(dv, 'errorTitle', '') or ''),
                        'prompt': str(getattr(dv, 'prompt', '') or ''),
                        'imeMode': getattr(dv, 'imeMode', None),
                    }
                return result

            dv_m = get_dv_summary(ws_m)
            dv_c = get_dv_summary(ws_c)
            all_refs = sorted(set(list(dv_m.keys()) + list(dv_c.keys())))

            for ref in all_refs:
                dm = dv_m.get(ref)
                dc = dv_c.get(ref)

                if dm is None and dc is not None:
                    diffs.append({
                        'category': 'シート設定',
                        'item': f'入力規則: {sheet_name} [{ref}]',
                        'master': '(なし)',
                        'check': str(dc),
                        'detail': f'入力規則が原本に存在しない (範囲: {ref})'
                    })
                    continue
                if dm is not None and dc is None:
                    diffs.append({
                        'category': 'シート設定',
                        'item': f'入力規則: {sheet_name} [{ref}]',
                        'master': str(dm),
                        'check': '(なし)',
                        'detail': f'入力規則が比較データに存在しない (範囲: {ref})'
                    })
                    continue

                label_map = {
                    'type': '規則の種類',
                    'operator': '演算子',
                    'formula1': '値1',
                    'formula2': '値2',
                    'showDropDown': 'ドロップダウン表示',
                    'allow_blank': '空白を無視',
                    'error': 'エラーメッセージ',
                    'errorTitle': 'エラータイトル',
                    'imeMode': '日本語入力モード',
                }
                for key, label in label_map.items():
                    vm = dm.get(key)
                    vc = dc.get(key)
                    if vm != vc:
                        diffs.append({
                            'category': 'シート設定',
                            'item': f'入力規則({label}): {sheet_name} [{ref}]',
                            'master': str(vm) if vm is not None else '(なし)',
                            'check': str(vc) if vc is not None else '(なし)',
                            'detail': f'入力規則の{label}が違う (範囲: {ref})'
                        })
        except Exception:
            pass
        return diffs

    # ------------------------------------------------------------------
    # No.99/100: ブックプロパティ（タイトル・作成者）
    # ------------------------------------------------------------------
    def _compare_book_properties(self, wb_m, wb_c):
        diffs = []
        try:
            props_m = getattr(wb_m, 'properties', None)
            props_c = getattr(wb_c, 'properties', None)

            prop_map = {
                'title':    ('ブックのタイトル',  'タイトルが違う'),
                'subject':  ('サブジェクト',     'サブジェクトが違う'),
                'creator':  ('作成者',          '作成者が違う'),
                'company':  ('会社名',          '会社名が違う'),
                'category': ('カテゴリ',         'カテゴリが違う'),
            }
            for attr, (label, detail) in prop_map.items():
                vm = str(getattr(props_m, attr, None) or '') if props_m else ''
                vc = str(getattr(props_c, attr, None) or '') if props_c else ''
                if vm != vc:
                    diffs.append({
                        'category': 'ブック設定',
                        'item': label,
                        'master': vm if vm else '(未設定)',
                        'check':  vc if vc else '(未設定)',
                        'detail': detail
                    })
        except Exception:
            pass
        return diffs
