#!/usr/bin/env python3

# Licensed under the terms of the GPL2, see LICENSE file.
# Copyright (c) 2013 jesuscfv <jesus.cfv@gmail.com>
# Copyright (c) 2014 Colin O'Flynn <coflynn@newae.com>
# Copyright (c) 2022 Julian Heinzel <jeinzi@gmx.de>

import sys
import os
import subprocess
import tkinter, tkinter.messagebox, tkinter.filedialog

import graphtec
import pic
import optimize
import config


def updateConfigDict():
    cnf["inputPath"] = Gerber_name.get()
    cnf["outputPath"] = Output_name.get()
    cnf["gerbvPath"] = gerbv_path.get()
    cnf["ghostscriptPath"] = ghostscript_path.get()
    cnf["pstoeditPath"] = pstoedit_path.get()
    cnf["offset"] = floats(offset_str.get())
    cnf["border"] = floats(border_str.get())
    cnf["matrix"] = floats(matrix_str.get())
    cnf["speed"] = floats(speed_str.get())
    cnf["force"] = floats(force_str.get())
    cnf["cutMode"] = int(cut_mode_str.get())
    cnf["deviceName"] = cutter_shared_name_str.get()


def floats(s):
  return list(map(float,s.split(',')))


def saveConfig():
  updateConfigDict()
  config.writeConfigFile(cnf)


def createForceTestFile():
  updateConfigDict()
  original_stdout = sys.stdout  # keep a reference to STDOUT

  if cnf["outputPath"] != "":
    sys.stdout = open(cnf["outputPath"], 'w')


  g = graphtec.graphtec()
  g.start()
  g.set(offset=cnf["offset"], matrix=cnf["matrix"], speed=cnf["speed"])

  for i in range(0, 6):
    for j in range(0, 5):
      g.set(force=1 + j + 5 * i)
      tx = 0.5 * j
      ty = 0.5 * i
      g.closed_path([(tx, ty), (tx + 0.3, ty), (tx + 0.3, ty + 0.3), (tx, ty + 0.3)])

  g.end()

  if cnf["outputPath"]:
    sys.stdout = original_stdout  # restore STDOUT back to its original value
    tkinter.messagebox.showinfo("SMTCut Message", f"File '{cnf['outputPath']}' created")




def showGerber():
  updateConfigDict()
  if not os.path.exists(cnf["inputPath"]):
    selectInputFile()
  if not os.path.exists(cnf["inputPath"]):
    tkinter.messagebox.showerror("SMTCut Error", "The path provided for the input Gerber file is invalid.")
    return

  head, tail = os.path.split(cnf["inputPath"])

  if os.name == 'nt':
    if not os.path.exists(cnf["gerbvPath"]):
      tkinter.messagebox.showerror("SMTCut Error", "The path provided for gerbv is invalid.")
      return

  subprocess.Popen([os.path.normpath(cnf["gerbvPath"]), os.path.normpath(cnf["inputPath"])])




def convertInput():
  # Convert file to PIC format.
  updateConfigDict()

  if not os.path.exists(cnf["inputPath"]):
    selectInputFile()
  if not os.path.exists(cnf["inputPath"]):
    tkinter.messagebox.showerror("SMTCut Error", "The path provided for the input Gerber file is invalid.")
    return

  head, tail = os.path.split(cnf["inputPath"])

  if os.name=='nt':
    temp_pdf = os.path.normpath(f"{head}\_tmp_gerber.pdf")
    temp_ps  = os.path.normpath(f"{head}\_tmp_gerber.ps" )
    temp_pic = os.path.normpath(f"{head}\_tmp_gerber.pic")
    temp_bat = os.path.normpath(f"{head}\_tmp_gerber.bat")
  else:
    temp_pdf = "_tmp_gerber.pdf"
    temp_ps  = "_tmp_gerber.ps"
    temp_pic = "_tmp_gerber.pic"

  gerbv = os.path.normpath(cnf["gerbvPath"])
  ghostscript = os.path.normpath(cnf["ghostscriptPath"])
  pstoedit = os.path.normpath(cnf["pstoeditPath"])
  gerberNormpath = os.path.normpath(cnf["inputPath"])

  if os.name=='nt':
    if not os.path.exists(gerbv):
      tkinter.messagebox.showerror("SMTCut Error", "The path provided for gerbv is invalid.")
      return
    if not os.path.exists(ghostscript):
      tkinter.messagebox.showerror("SMTCut Error", "The path provided for Ghostscript is invalid.")
      return
    if not os.path.exists(pstoedit):
      tkinter.messagebox.showerror("SMTCut Error", "The path provided for pstoedit is invalid.")
      return

  
  if os.name=='nt':
    os.system(f'echo "{gerbv}" --export=pdf --output="{temp_pdf}" --border=0 "{gerberNormpath}" > "{temp_bat}"')
    os.system(f'echo "{ghostscript}" -dNOPAUSE -dBATCH -sDEVICE=ps2write -sOutputFile="{temp_ps}" "{temp_pdf}" >> "{temp_bat}"')
    os.system(f'echo "{pstoedit}" -q -f pic "{temp_ps}" "{temp_pic}" >> "{temp_bat}"')
    os.system(temp_bat)
  else:
    os.system(f"'{gerbv}' --export=pdf --output='{temp_pdf}' --border=0 '{gerberNormpath}'")
    os.system(f"'{ghostscript}' -dNOPAUSE -dBATCH -sDEVICE=ps2write -sOutputFile='{temp_ps}' '{temp_pdf}'")
    os.system(f"'{pstoedit}' -q -f pic '{temp_ps}' '{temp_pic}'")

  original_stdout = sys.stdout  # keep a reference to STDOUT

  if cnf["outputPath"]:
    sys.stdout = open(cnf["outputPath"], 'w')


  # Main program.
  g = graphtec.graphtec()
  g.start()

  border = cnf["border"]
  g.set(offset=(cnf["offset"][0]+border[0]+0.5,cnf["offset"][1]+border[1]+0.5), matrix=cnf["matrix"])
  strokes = pic.read_pic(temp_pic)
  max_x,max_y = optimize.max_extent(strokes)

  border_path = [
    (-border[0], -border[1]),
    (max_x+border[0], -border[1]),
    (max_x+border[0], max_y+border[1]),
    (-border[0], max_y+border[1])
  ]

  if cnf["cutMode"] == 0:
    lines = optimize.optimize(strokes, border)
    for (s,f) in zip(cnf["speed"], cnf["force"]):
      g.set(speed=s, force=f)
      for x in lines:
        g.line(*x)
      g.closed_path(border_path)
  else:
    for (s,f) in zip(cnf["speed"], cnf["force"]):
      g.set(speed=s, force=f)
      for s in strokes:
        g.closed_path(s)
      g.closed_path(border_path)

  g.end()

  if Output_name.get():
    sys.stdout = original_stdout  # restore STDOUT back to its original value
    tkinter.messagebox.showinfo("SMTCut Message", f"File '{Output_name.get()}' created")


def exitGui():
    top.destroy()


def startCutting():
    updateConfigDict()
    if not cnf["outputPath"]:
      selectOutputFile()
    if not cnf["outputPath"]:
      return
    src=os.path.normpath(cnf["outputPath"])

    if cnf["deviceName"] == "":
      tkinter.messagebox.showerror("SMTCut Error", "The name of the cutter (as a shared printer) was not provided.")
      return

    if not os.path.isfile(src):
      tkinter.messagebox.showerror("SMTCut Error", "The Graphtec output file has not been generated, please press the 'Create Graphtec File' button first.")
      return

    dst = os.path.normpath(cnf["deviceName"])
    try:
      with open(src, 'r') as f, open(dst, 'w') as lpt:
        while True:
          buf = f.read()
          if not buf: break
          lpt.write(buf)
    except:
      tkinter.messagebox.showerror("SMTCut Error", "There was an error sending the Graphtec file to the plotter")
      return


def selectInputFile():
    input_filename=tkinter.filedialog.askopenfilename(title='Select paste mask Gerber file', filetypes=[('Gerber File', ('*.g*', '*.G*')),("All files", "*.*")])
    if input_filename:
        Gerber_name.set(input_filename)

def selectOutputFile():
    output_filename=tkinter.filedialog.asksaveasfilename(title='Select output filename', filetypes=[('Output files', '*.txt'),("All files", "*.*")] )
    if output_filename:
        Output_name.set(output_filename)

def selectGerbvExe():
    gerbv_filename=tkinter.filedialog.askopenfilename(title='Select gerbv program', initialfile='gerbv.exe', filetypes=[('Programs', '*.exe')] )
    if gerbv_filename:
        gerbv_path.set(gerbv_filename)

def selectPstoeditExe():
    pstoedit_filename=tkinter.filedialog.askopenfilename(title='Select gerbv program', initialfile='pstoedit.exe', filetypes=[('Programs', '*.exe')] )
    if pstoedit_filename:
        pstoedit_path.set(pstoedit_filename)

def selectGhostscriptExe():
    ghostscript_filename=tkinter.filedialog.askopenfilename(title='Select Ghostscript program', initialfile='ghostscript.exe', filetypes=[('Programs', '*.exe')] )
    if ghostscript_filename:
        ghostscript_path.set(ghostscript_filename)


def selectAll(event):
    # Select text.
    event.widget.select_range(0, 'end')
    # Move cursor to the end.
    event.widget.icursor('end')
    # Stop event propagation.
    return "break"


def arrToStr(a):
    return str(a).strip("[]").replace(" ", "")

def getDefaultValue(key, textfieldStr):
    defaultValue = config.getDefaultConfig()[key]
    textfieldStr.set(arrToStr(defaultValue))




if __name__ == "__main__":
    top = tkinter.Tk()
    top.title("SMTCut")
    cnf = config.getConfig()

    # Create variables that bind to text fields and fill them with
    # values from config manager.
    Gerber_name = tkinter.StringVar(top, cnf["inputPath"])
    Output_name = tkinter.StringVar(top, cnf["outputPath"])
    gerbv_path = tkinter.StringVar(top, cnf["gerbvPath"])
    ghostscript_path = tkinter.StringVar(top, cnf["ghostscriptPath"])
    pstoedit_path = tkinter.StringVar(top, cnf["pstoeditPath"])
    offset_str = tkinter.StringVar(top, arrToStr(cnf["offset"]))
    border_str = tkinter.StringVar(top, arrToStr(cnf["border"]))
    matrix_str = tkinter.StringVar(top, arrToStr(cnf["matrix"]))
    speed_str = tkinter.StringVar(top, arrToStr(cnf["speed"]))
    force_str = tkinter.StringVar(top, arrToStr(cnf["force"]))
    cut_mode_str = tkinter.StringVar(top, cnf["cutMode"])
    cutter_shared_name_str = tkinter.StringVar(top, cnf["deviceName"])

    # Add input text fields.
    row = 1
    def addInputRow(title, textVariable, buttonText, command):
        global row
        tkinter.Label(top, text=title).grid(row=row, column=0, sticky=tkinter.W)
        entry = tkinter.Entry(top, bd=1, width=60, textvariable=textVariable)
        entry.bind('<Control-a>', selectAll)
        entry.grid(row=row, column=1)
        if buttonText != "":
            tkinter.Button(top, width=9, text=buttonText, command=command).grid(row=row, column=2)
        row += 1

    addInputRow("Input File", Gerber_name, "Browse", selectInputFile)
    addInputRow("Output File", Output_name, "Browse", selectOutputFile)

    if os.name == "nt":
        addInputRow("gerbv path", gerbv_path, "Browse", selectGerbvExe)
        addInputRow("Ghostscript path", ghostscript_path, "Browse", selectGhostscriptExe)
        addInputRow("pstoedit path", pstoedit_path, "Browse", selectPstoeditExe)

    addInputRow("Offset", offset_str, "Default", lambda: getDefaultValue("offset", offset_str))
    addInputRow("Border", border_str, "Default", lambda: getDefaultValue("border", border_str))
    addInputRow("Matrix", matrix_str, "Default", lambda: getDefaultValue("matrix", matrix_str))
    addInputRow("Speed", speed_str, "Default", lambda: getDefaultValue("speed", speed_str))
    addInputRow("Force", force_str, "Default", lambda: getDefaultValue("force", force_str))
    addInputRow("Cut Mode", cut_mode_str, "Default", lambda: getDefaultValue("cutMode", cut_mode_str))

    labelText = "Cutter Shared Name" if os.name == "nt" else "Cutter Device Name"
    addInputRow(labelText, cutter_shared_name_str, "", None)

    # Create main button area.
    def addButtonRow(text, command):
        global row
        tkinter.Button(top, width=40, text=text, command=command).grid(row=row, column=1)
        row += 1
    addButtonRow("Show Gerber", showGerber)
    addButtonRow("Create Graphtec File from input", convertInput)
    addButtonRow("Send Graphtec File to Silhouette Cutter", startCutting)
    addButtonRow("Save Configuration", saveConfig)
    addButtonRow("Create force testing Graphtec file", createForceTestFile)
    addButtonRow("Exit", exitGui)

    top.mainloop()
