# modules/cell_comparator.py
"""セル比較モジュール (バグ修正版 v1.1)"""

from difflib import SequenceMatcher


class CellComparator:

    def __init__(self):
        self.differences = []

    def create_strict_string(self, cell_data):
        raw_val = cell_data.get('value')
        if raw_val is None:
            val = ''
        elif isinstance(raw_val, (int, float)):
            val = str(round(float(raw_val), 10))
        else:
            val = str(raw_val)
        dtype = cell_data.get('data_type', 'n/a')
        nformat = cell_data.get('number_format', 'General')
        return f"{val}::{dtype}::{nformat}"

    def compare(self, cell_master, cell_check, position):
        diffs = []
        strict_m = self.create_strict_string(cell_master)
        strict_c = self.create_strict_string(cell_check)

        if strict_m == strict_c:
            diffs.extend(self._compare_format(cell_master, cell_check))
        else:
            for fn in [self._compare_value, self._compare_data_type, self._compare_number_format]:
                d = fn(cell_master, cell_check)
                if d:
                    diffs.append(d)
            diffs.extend(self._compare_format(cell_master, cell_check))

        for fn in [self._compare_merged, self._compare_hidden, self._compare_hyperlink,
                   self._compare_protection, self._compare_comment]:
            d = fn(cell_master, cell_check)
            if d:
                diffs.append(d)

        if diffs:
            return {'position': position, 'differences': diffs,
                    'master': cell_master, 'check': cell_check}
        return None

    def _format_visible(self, val):
        if val is None:
            return "(空白セル)"
        # 論理値型はExcel表記に合わせてTRUE/FALSEで返す
        # （bool はintのサブクラスなので他の型チェックより先に判定する）
        if isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        # 日付・日時型はそのまま日本語形式で返す（Pythonのstr()は使わない）
        from datetime import datetime, date as date_type
        if isinstance(val, (datetime, date_type)):
            return f"{val.year}/{val.month}/{val.day}"
        text = str(val)
        if text == "":
            return "(空文字)"
        import re
        # Excelエラー値・エラー数式の日本語表示
        ERROR_VALUES = {
            '#N/A':    '#N/A（該当なし）',
            '#REF!':   '#REF!（参照エラー）',
            '#VALUE!': '#VALUE!（値エラー）',
            '#DIV/0!': '#DIV/0!（ゼロ除算エラー）',
            '#NAME?':  '#NAME?（名前エラー）',
            '#NUM!':   '#NUM!（数値エラー）',
            '#NULL!':  '#NULL!（NULLエラー）',
        }
        ERROR_FORMULAS = {
            '=na()':      '=NA()（該当なし）',
            '=iferror()': '=IFERROR()（エラー処理数式）',
            '=1/0':       '=1/0（ゼロ除算エラーを返す数式）',
        }
        if text in ERROR_VALUES:
            return ERROR_VALUES[text]
        if text.lower() in ERROR_FORMULAS:
            return ERROR_FORMULAS[text.lower()]
        # 1文字ずつ処理してアノテーションをインラインで付与
        # （置換後テキストを再処理しないため、注記文字列が誤検出されない）
        result = ''
        for c in text:
            o = ord(c)
            # ゼロ幅・不可視文字
            if o in (0x200B, 0x200C, 0x200D, 0xFEFF):
                result += '（見えないスペース）'
            # 特殊スペース
            elif o == 0x00A0:   # NO-BREAK SPACE
                result += '（特殊スペース・半角幅）'
            elif o == 0x2003:   # EM SPACE
                result += '（特殊スペース・全角幅）'
            elif o == 0x2002:   # EN SPACE
                result += '（特殊スペース・半角幅）'
            # 制御文字
            elif c == '\n':
                result += '（改行）'
            elif c == '\r':
                result += '（改行CR）'
            elif c == '\t':
                result += '（タブ）'
            # スペース類
            elif o == 0x3000:   # IDEOGRAPHIC SPACE（全角スペース）
                result += '（全角スペース）'
            elif c == ' ':      # U+0020 半角スペース
                result += '（半角スペース）'
            # 波ダッシュ（U+301C）— 全角チルダ（～ U+FF5E）や半角チルダ（~ U+007E）と混同されやすい
            elif o == 0x301C:
                result += '〜（波）'
            # 半角カナ [ｦ-ﾟ]
            elif re.match(r'[ｦ-ﾟ]', c):
                result += c + '（半角）'
            # 全角カナ [ァ-ン]
            elif re.match(r'[ァ-ン]', c):
                result += c + '（全角）'
            # 全角ASCII [！-～] (U+FF01-U+FF5E)
            elif re.match(r'[！-～]', c):
                result += c + '（全角）'
            # 半角ASCII記号（英数字・スペース除く、印刷可能文字）
            elif c.isascii() and c.isprintable() and not c.isalnum() and c != ' ':
                result += c + '（半角）'
            else:
                result += c
        return result

    def _compare_value(self, cell_m, cell_c):
        val_m = cell_m['value']
        val_c = cell_c['value']
        if val_m is None and val_c is None:
            return None
        if val_m is None or val_c is None:
            return {'type': 'value',
                    'master': self._format_visible(val_m),
                    'check': self._format_visible(val_c),
                    'detail': '入力内容が違う（片方が空白）',
                    'diff_positions': []}
        if isinstance(val_m, (int, float)) and isinstance(val_c, (int, float)):
            if round(float(val_m), 10) != round(float(val_c), 10):
                return {'type': 'value', 'master': str(val_m), 'check': str(val_c),
                        'detail': f'数値が違う: {val_m} -> {val_c}', 'diff_positions': []}
            return None
        val_m_str = str(val_m)
        val_c_str = str(val_c)
        if val_m_str != val_c_str:
            return {'type': 'value',
                    'master': self._format_visible(val_m),
                    'check': self._format_visible(val_c),
                    'detail': '入力内容が違う',
                    'diff_positions': self._find_string_diff(val_m_str, val_c_str)}
        return None

    def _compare_data_type(self, cell_m, cell_c):
        type_labels = {'n': '数値型', 's': '文字列型', 'b': '論理値型', 'd': '日付型',
                       'e': 'エラー型', 'f': '数式型', 'inlineStr': '文字列型',
                       'str': '文字列型', 'n/a': '不明'}
        dtype_m = cell_m.get('data_type', '')
        dtype_c = cell_c.get('data_type', '')
        if dtype_m != dtype_c:
            lm = type_labels.get(dtype_m, dtype_m)
            lc = type_labels.get(dtype_c, dtype_c)
            mv = cell_m.get('value')
            cv = cell_c.get('value')
            # 空白セルは型なし扱い
            if mv is None:
                lm = "なし（空白セル）"
            if cv is None:
                lc = "なし（空白セル）"
            return {'type': 'data_type',
                    'master': lm, 'check': lc,
                    'master_value': mv,
                    'check_value': cv,
                    'detail': f"データの型が違う: {lm} -> {lc}"}
        return None

    def _compare_number_format(self, cell_m, cell_c):
        fmt_m = (cell_m.get('number_format') or 'General').strip()
        fmt_c = (cell_c.get('number_format') or 'General').strip()
        nm = fmt_m.lower() if fmt_m.lower() == 'general' else fmt_m
        nc = fmt_c.lower() if fmt_c.lower() == 'general' else fmt_c
        if nm != nc:
            return {'type': 'number_format', 'master': fmt_m, 'check': fmt_c,
                    'master_value': cell_m.get('value'),
                    'check_value': cell_c.get('value'),
                    'detail': f'表示形式が違う: "{fmt_m}" -> "{fmt_c}"'}
        return None

    def _compare_format(self, cell_m, cell_c):
        diffs = []

        # ── 翻訳マップ ──────────────────────────────────────────
        BORDER_STYLE = {
            None: '罫線なし', 'thin': '細線', 'thick': '太線',
            'medium': '中線', 'dashed': '破線', 'dotted': '点線',
            'double': '二重線', 'hair': '極細線',
            'mediumDashed': '中破線', 'dashDot': '一点鎖線',
            'mediumDashDot': '中一点鎖線', 'dashDotDot': '二点鎖線',
            'mediumDashDotDot': '中二点鎖線', 'slantDashDot': '斜め一点鎖線',
        }
        BORDER_SIDE = {'top': '上', 'bottom': '下', 'left': '左', 'right': '右'}
        H_ALIGN = {
            None: '標準', 'general': '標準', 'center': '中央揃え',
            'left': '左揃え', 'right': '右揃え', 'fill': '繰り返し',
            'justify': '均等割り付け', 'centerContinuous': '選択範囲内で中央',
            'distributed': '均等割り付け（均等）',
        }
        V_ALIGN = {
            None: '設定なし', 'top': '上揃え', 'center': '中央揃え',
            'bottom': '下揃え', 'justify': '均等割り付け',
            'distributed': '均等割り付け（均等）',
        }
        UNDERLINE = {
            None: 'なし', 'single': '下線（単線）', 'double': '下線（二重線）',
            'singleAccounting': '下線（会計・単線）',
            'doubleAccounting': '下線（会計・二重線）',
        }
        VERT_ALIGN = {
            None: '標準', 'baseline': '標準',
            'superscript': '上付き', 'subscript': '下付き',
        }
        BOOL_JA = {True: 'あり', False: 'なし', None: 'なし'}

        def _bs(v):
            return BORDER_STYLE.get(v, str(v) if v is not None else '罫線なし')

        def _tr(v, mapping):
            return mapping.get(v, str(v) if v is not None else 'なし')

        # ── フォント ────────────────────────────────────────────
        font_m = cell_m.get('font', {})
        font_c = cell_c.get('font', {})

        font_checks = [
            ('font_name',       'name',       'フォント名',     None),
            ('font_size',       'size',       'フォントサイズ', None),
            ('font_bold',       'bold',       '太字',           BOOL_JA),
            ('font_italic',     'italic',     '斜体',           BOOL_JA),
            ('font_underline',  'underline',  '下線',           UNDERLINE),
            ('font_strike',     'strike',     '取り消し線',     BOOL_JA),
            ('font_vert_align', 'vert_align', '上付き・下付き', VERT_ALIGN),
        ]
        for typ, key, label, mapping in font_checks:
            vm, vc = font_m.get(key), font_c.get(key)
            if vm != vc:
                vm_ja = _tr(vm, mapping) if mapping else (str(vm) if vm is not None else 'なし')
                vc_ja = _tr(vc, mapping) if mapping else (str(vc) if vc is not None else 'なし')
                diffs.append({'type': typ, 'master': vm_ja, 'check': vc_ja,
                               'detail': f"{label}: {vm_ja} -> {vc_ja}"})

        if font_m.get('color') != font_c.get('color'):
            diffs.append({'type': 'font_color', 'master': font_m.get('color'),
                           'check': font_c.get('color'), 'detail': '文字色が違う'})

        # ── 塗りつぶし ──────────────────────────────────────────
        fill_m = cell_m.get('fill', {})
        fill_c = cell_c.get('fill', {})
        if fill_m.get('start_color') != fill_c.get('start_color'):
            diffs.append({'type': 'fill_color', 'master': fill_m.get('start_color'),
                           'check': fill_c.get('start_color'), 'detail': '背景色が違う'})

        # ── 罫線 ────────────────────────────────────────────────
        border_m = cell_m.get('border', {})
        border_c = cell_c.get('border', {})
        for side in ['top', 'bottom', 'left', 'right']:
            side_ja = BORDER_SIDE[side]
            bm, bc = border_m.get(side), border_c.get(side)
            if bm != bc:
                diffs.append({'type': f'border_{side}',
                               'master': _bs(bm), 'check': _bs(bc),
                               'detail': f'{side_ja}罫線スタイルが違う: {_bs(bm)} -> {_bs(bc)}'})
            ck = f'{side}_color'
            if border_m.get(ck) != border_c.get(ck):
                diffs.append({'type': f'border_{side}_color',
                               'master': border_m.get(ck), 'check': border_c.get(ck),
                               'detail': f'{side_ja}罫線の色が違う: {border_m.get(ck)} -> {border_c.get(ck)}'})

        # ── 配置 ────────────────────────────────────────────────
        align_m = cell_m.get('alignment', {})
        align_c = cell_c.get('alignment', {})

        hm, hc = align_m.get('horizontal'), align_c.get('horizontal')
        if hm != hc:
            hm_ja, hc_ja = _tr(hm, H_ALIGN), _tr(hc, H_ALIGN)
            diffs.append({'type': 'alignment_horizontal', 'master': hm_ja, 'check': hc_ja,
                           'detail': f"水平配置: {hm_ja} -> {hc_ja}"})

        vm2, vc2 = align_m.get('vertical'), align_c.get('vertical')
        if vm2 != vc2:
            vm2_ja, vc2_ja = _tr(vm2, V_ALIGN), _tr(vc2, V_ALIGN)
            diffs.append({'type': 'alignment_vertical', 'master': vm2_ja, 'check': vc2_ja,
                           'detail': f"垂直配置: {vm2_ja} -> {vc2_ja}"})

        rm, rc = align_m.get('text_rotation'), align_c.get('text_rotation')
        if rm != rc:
            rm_ja = f"{rm}度" if rm is not None else "なし"
            rc_ja = f"{rc}度" if rc is not None else "なし"
            diffs.append({'type': 'alignment_text_rotation', 'master': rm_ja, 'check': rc_ja,
                           'detail': f"テキスト角度: {rm_ja} -> {rc_ja}"})

        im, ic = align_m.get('indent', 0), align_c.get('indent', 0)
        if im != ic:
            diffs.append({'type': 'alignment_indent', 'master': im, 'check': ic,
                           'detail': f"インデント: {im} -> {ic}"})

        wm, wc = bool(align_m.get('wrap_text')), bool(align_c.get('wrap_text'))
        if wm != wc:
            wm_ja = BOOL_JA.get(align_m.get('wrap_text'), 'あり' if wm else 'なし')
            wc_ja = BOOL_JA.get(align_c.get('wrap_text'), 'あり' if wc else 'なし')
            diffs.append({'type': 'alignment_wrap_text',
                           'master': wm_ja, 'check': wc_ja,
                           'detail': f"折り返し表示: {wm_ja} -> {wc_ja}"})

        sm, sc = bool(align_m.get('shrink_to_fit')), bool(align_c.get('shrink_to_fit'))
        if sm != sc:
            sm_ja = BOOL_JA.get(align_m.get('shrink_to_fit'), 'あり' if sm else 'なし')
            sc_ja = BOOL_JA.get(align_c.get('shrink_to_fit'), 'あり' if sc else 'なし')
            diffs.append({'type': 'alignment_shrink_to_fit',
                           'master': sm_ja, 'check': sc_ja,
                           'detail': f"縮小して全体を表示: {sm_ja} -> {sc_ja}"})

        return diffs

    def _compare_merged(self, cell_m, cell_c):
        mm = cell_m.get('is_merged')
        mc = cell_c.get('is_merged')
        if mm != mc:
            mm_ja = mm if mm is not None else '結合なし'
            mc_ja = mc if mc is not None else '結合なし'
            return {'type': 'merged', 'master': mm_ja, 'check': mc_ja,
                    'detail': f"結合範囲が違う: {mm_ja} -> {mc_ja}"}
        return None

    def _compare_hidden(self, cell_m, cell_c):
        hm = cell_m.get('is_hidden', False)
        hc = cell_c.get('is_hidden', False)
        if hm != hc:
            return {'type': 'hidden', 'master': hm, 'check': hc,
                    'detail': f"非表示状態が違う: {hm} -> {hc}"}
        return None

    def _compare_hyperlink(self, cell_m, cell_c):
        hl_m = cell_m.get('hyperlink')
        hl_c = cell_c.get('hyperlink')
        if hl_m != hl_c:
            return {'type': 'hyperlink', 'master': hl_m, 'check': hl_c,
                    'detail': f"ハイパーリンクURLが違う: {hl_m} -> {hl_c}"}
        return None

    def _compare_protection(self, cell_m, cell_c):
        prot_m = cell_m.get('protection', {}) or {}
        prot_c = cell_c.get('protection', {}) or {}
        diffs = []
        # locked (No.39)
        lm = prot_m.get('locked')
        lc = prot_c.get('locked')
        lm_bool = lm if lm is not None else True
        lc_bool = lc if lc is not None else True
        if lm_bool != lc_bool:
            diffs.append({'type': 'protection_locked',
                          'master': lm_bool, 'check': lc_bool,
                          'detail': f'セルのロック設定が違う: {lm_bool} -> {lc_bool}'})
        hm = prot_m.get('hidden_formula')
        hc = prot_c.get('hidden_formula')
        hm_bool = bool(hm) if hm is not None else False
        hc_bool = bool(hc) if hc is not None else False
        if hm_bool != hc_bool:
            diffs.append({'type': 'protection_hidden_formula',
                          'master': hm_bool, 'check': hc_bool,
                          'detail': f'数式の非表示設定が違う: {hm_bool} -> {hc_bool}'})
        if len(diffs) == 0:
            return None
        if len(diffs) == 1:
            return diffs[0]
        return {'type': 'protection_locked',
                'master': f"ロック:{lm_bool}, 非表示:{hm_bool}",
                'check': f"ロック:{lc_bool}, 非表示:{hc_bool}",
                'detail': 'セル保護設定が違う'}

    def _compare_comment(self, cell_m, cell_c):
        cm = cell_m.get('comment')
        cc = cell_c.get('comment')
        if cm == cc:
            return None
        if cm is None or cc is None:
            has = cm if cm is not None else cc
            return {'type': 'comment',
                    'master': f"テキスト:{cm['text']}, 作成者:{cm['author']}" if cm else '(なし)',
                    'check': f"テキスト:{cc['text']}, 作成者:{cc['author']}" if cc else '(なし)',
                    'detail': 'コメント・メモの有無が違う'}
        details = []
        if cm.get('text') != cc.get('text'):
            details.append('テキスト違い')
        if cm.get('author') != cc.get('author'):
            details.append(f"作成者違い: {cm.get('author')} -> {cc.get('author')}")
        if details:
            return {'type': 'comment',
                    'master': f"テキスト:{cm['text']}, 作成者:{cm['author']}",
                    'check': f"テキスト:{cc['text']}, 作成者:{cc['author']}",
                    'detail': ', '.join(details)}

    def _find_string_diff(self, str_m, str_c):
        matcher = SequenceMatcher(None, str_m, str_c)
        result = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                result.append({'type': tag,
                                'master_range': (i1, i2), 'check_range': (j1, j2),
                                'master_text': str_m[i1:i2], 'check_text': str_c[j1:j2]})
        return result
