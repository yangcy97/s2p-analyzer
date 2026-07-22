# -*- coding: utf-8 -*-
"""
s2p_gui.py
Free-space S-parameter Analyzer (S33/S43/S34/S44 -> full EM property CSV)
Simple GUI: Browse .s2p -> enter thickness(mm) -> Run -> Save CSV
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

from s2p_calc import compute_all


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Free-Space S-Parameter Analyzer (Mode 1)")
        self.geometry("560x230")
        self.resizable(False, False)

        self.filepath = tk.StringVar()
        self.thickness = tk.StringVar(value="2.0")

        pad = {"padx": 10, "pady": 8}

        # --- File selection row ---
        tk.Label(self, text="S2P 파일:").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.filepath, width=50, state="readonly").grid(
            row=0, column=1, **pad)
        tk.Button(self, text="찾아보기...", command=self.browse_file).grid(
            row=0, column=2, **pad)

        # --- Thickness row ---
        tk.Label(self, text="시료 두께 (mm):").grid(row=1, column=0, sticky="w", **pad)
        tk.Entry(self, textvariable=self.thickness, width=15).grid(
            row=1, column=1, sticky="w", **pad)

        # --- Run button ---
        tk.Button(self, text="확인 (계산 실행 -> CSV 저장)", command=self.run_calc,
                  bg="#2d6cdf", fg="white", height=2, width=30).grid(
            row=2, column=0, columnspan=3, pady=20)

        # --- Status label ---
        self.status = tk.StringVar(value="s2p 파일을 선택하고 두께를 입력하세요.")
        tk.Label(self, textvariable=self.status, fg="gray20", wraplength=520,
                 justify="left").grid(row=3, column=0, columnspan=3, sticky="w", **pad)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="S2P 파일 선택",
            filetypes=[("S-parameter files", "*.s2p *.S2P"), ("All files", "*.*")]
        )
        if path:
            self.filepath.set(path)
            self.status.set(f"선택된 파일: {os.path.basename(path)}")

    def run_calc(self):
        path = self.filepath.get().strip()
        if not path:
            messagebox.showwarning("알림", "s2p 파일을 먼저 선택하세요.")
            return
        if not os.path.exists(path):
            messagebox.showerror("오류", "파일을 찾을 수 없습니다.")
            return

        try:
            thickness_mm = float(self.thickness.get().strip())
            if thickness_mm <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("알림", "두께는 0보다 큰 숫자(mm)로 입력하세요.")
            return

        try:
            self.status.set("계산 중입니다...")
            self.update_idletasks()
            df = compute_all(path, thickness_mm)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("계산 오류", f"계산 중 오류가 발생했습니다:\n{e}")
            self.status.set("오류가 발생했습니다. 파일 형식을 확인하세요.")
            return

        default_name = os.path.splitext(os.path.basename(path))[0] + "_result.csv"
        save_path = filedialog.asksaveasfilename(
            title="결과 CSV 저장",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")]
        )
        if not save_path:
            self.status.set("저장이 취소되었습니다.")
            return

        try:
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
        except Exception as e:
            messagebox.showerror("저장 오류", f"CSV 저장 중 오류:\n{e}")
            return

        n_total = len(df)
        n_nonphysical = int((~df["passivity_flag"]).sum())
        msg = f"완료되었습니다.\n\n행(주파수 포인트) 수: {n_total}\n저장 위치: {save_path}"
        if n_nonphysical > 0:
            msg += (f"\n\n[참고] {n_nonphysical}개 주파수 포인트에서 "
                    f"eps'' 또는 mu''가 음수(비물리적)로 계산되었습니다.\n"
                    f"'passivity_flag' 컬럼이 False인 구간은 캘리브레이션/"
                    f"다층구조 영향일 수 있으니 참고하여 해석하세요.")
        self.status.set("완료되었습니다. 새로운 파일을 분석하려면 파일을 다시 선택하세요.")
        messagebox.showinfo("완료", msg)


if __name__ == "__main__":
    app = App()
    app.mainloop()
