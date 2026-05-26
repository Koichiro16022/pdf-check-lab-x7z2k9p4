# modules/image_comparator.py
"""
画像比較モジュール
位置・サイズ・内容を比較（1%閾値）
"""

import streamlit as st
from PIL import Image as PILImage, ImageChops
import hashlib
import numpy as np
from io import BytesIO

class ImageComparator:
    """画像比較クラス"""
    
    def __init__(self, threshold=0.01):
        """
        Args:
            threshold: 差分閾値（デフォルト1%）
        """
        self.threshold = threshold
        self.differences = []
    
    def compare(self, ws_master, ws_check):
        """
        シート内の全画像を比較
        
        Args:
            ws_master: 元データのワークシート
            ws_check: 比較データのワークシート
        
        Returns:
            list: 差異のリスト
        """
        try:
            images_m = ws_master._images if hasattr(ws_master, '_images') else []
            images_c = ws_check._images if hasattr(ws_check, '_images') else []
        except:
            images_m = []
            images_c = []
        
        results = []
        
        # 個数チェック
        if len(images_m) != len(images_c):
            results.append({
                'type': 'image_count',
                'master': len(images_m),
                'check': len(images_c),
                'detail': f'画像の個数が違う: 元{len(images_m)}枚 → 比較{len(images_c)}枚',
                'position': '全体'
            })
        
        # 各画像を比較
        for i, (img_m, img_c) in enumerate(zip(images_m, images_c)):
            diff = self._compare_single_image(img_m, img_c, i+1)
            if diff:
                results.append(diff)
        
        return results
    
    def _compare_single_image(self, img_m, img_c, index):
        """1枚の画像を比較"""
        
        position = self._get_position(img_m)
        
        # 位置チェック
        try:
            if str(img_m.anchor) != str(img_c.anchor):
                return {
                    'type': 'image_position',
                    'index': index,
                    'position': position,
                    'master': str(img_m.anchor),
                    'check': str(img_c.anchor),
                    'detail': f'画像{index}の位置が違う'
                }
        except:
            pass
        
        # サイズチェック
        try:
            if (img_m.width != img_c.width or 
                img_m.height != img_c.height):
                return {
                    'type': 'image_size',
                    'index': index,
                    'position': position,
                    'master': f'{img_m.width}×{img_m.height}',
                    'check': f'{img_c.width}×{img_c.height}',
                    'detail': f'画像{index}のサイズが違う'
                }
        except:
            pass
        
        # ハッシュ値チェック
        try:
            hash_m = self._get_hash(img_m)
            hash_c = self._get_hash(img_c)
            
            if hash_m == hash_c:
                return None  # 完全一致
            
            # 視覚的比較
            diff_ratio = self._visual_compare(img_m, img_c)
            
            if diff_ratio < self.threshold:
                return None  # 許容範囲内
            
            return {
                'type': 'image_content',
                'index': index,
                'position': position,
                'diff_ratio': diff_ratio,
                'detail': f'画像{index}の内容が{diff_ratio*100:.1f}%異なる'
            }
        
        except Exception as e:
            return {
                'type': 'image_error',
                'index': index,
                'position': position,
                'detail': f'画像{index}の比較エラー: {str(e)}'
            }
    
    @staticmethod
    def _get_hash(img):
        """画像のハッシュ値を取得"""
        try:
            return hashlib.md5(img._data()).hexdigest()
        except:
            return None
    
    @staticmethod
    def _visual_compare(img_m, img_c):
        """
        視覚的比較（サムネイル使用）
        
        Returns:
            float: 差分率（0.0-1.0）
        """
        try:
            # 画像を開く
            pil_m = PILImage.open(BytesIO(img_m._data()))
            pil_c = PILImage.open(BytesIO(img_c._data()))
            
            # サイズチェック
            if pil_m.size != pil_c.size:
                return 1.0  # 100%違う
            
            # サムネイル化（処理高速化）
            pil_m.thumbnail((100, 100))
            pil_c.thumbnail((100, 100))
            
            # RGB変換
            pil_m = pil_m.convert('RGB')
            pil_c = pil_c.convert('RGB')
            
            # 差分計算
            diff = ImageChops.difference(pil_m, pil_c)
            diff_array = np.array(diff)
            
            # 差分率
            diff_ratio = np.sum(diff_array) / (diff_array.size * 255)
            
            return diff_ratio
        
        except Exception as e:
            return 1.0  # エラー時は差異ありとする
    
    @staticmethod
    def _get_position(img):
        """画像の配置位置を取得"""
        try:
            anchor = img.anchor
            if hasattr(anchor, '_from'):
                from openpyxl.utils import get_column_letter
                col = anchor._from.col
                row = anchor._from.row
                return f"{get_column_letter(col+1)}{row+1}"
        except:
            pass
        return "不明"
