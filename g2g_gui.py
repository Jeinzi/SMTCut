#!/usr/bin/env python
import tkinter
import sys
import os
import string
import subprocess

import graphtec
import pic
import optimize
import config

from tkinter import *
from tkinter import filedialog, messagebox
from os import path, access, R_OK, W_OK

top = tkinter.Tk()
top.title("Gerber to Graphtec")

Gerber_name = StringVar()
Output_name = StringVar()
gerbv_path = StringVar()
ghostscript_path  = StringVar()
pstoedit_path  = StringVar()
offset_str  = StringVar()
border_str  = StringVar()
matrix_str  = StringVar()
speed_str  = StringVar()
force_str  = StringVar()
cut_mode_str  = StringVar()
cutter_shared_name_str  = StringVar()


cnf = config.getConfig()


def floats(s):
  return list(map(float,str.split(s,',')))


def saveConfig():
  updateConfigDict()
  config.writeConfigFile(cnf)


def test_forces():
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
    tkinter.messagebox.showinfo("G2G_GUI Message", "File '%s' created" % (cnf["outputPath"]))




def show_gerber():
  updateConfigDict()
  if not os.path.exists(cnf["inputPath"]):
    get_input_filename()
  if not os.path.exists(cnf["inputPath"]):
    tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for the input Gerber file is invalid.")
    return

  head, tail = os.path.split(cnf["inputPath"])

  if os.name == 'nt':
    if not os.path.exists(cnf["gerbvPath"]):
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for gerbv is invalid.")
      return

  subprocess.Popen([os.path.normpath(cnf["gerbvPath"]), os.path.normpath(cnf["inputPath"])])




def main_program():
  #
  # convert file to pic format
  #
  updateConfigDict()

  if not os.path.exists(cnf["inputPath"]):
    get_input_filename()
  if not os.path.exists(cnf["inputPath"]):
    tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for the input Gerber file is invalid.")
    return

  head, tail = os.path.split(cnf["inputPath"])

  if os.name=='nt':
    temp_pdf = os.path.normpath("%s\_tmp_gerber.pdf" % (head))
    temp_ps  = os.path.normpath("%s\_tmp_gerber.ps"  % (head))
    temp_pic = os.path.normpath("%s\_tmp_gerber.pic" % (head))
    temp_bat = os.path.normpath("%s\_tmp_gerber.bat" % (head))
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
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for gerbv is invalid.")
      return
    if not os.path.exists(ghostscript):
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for Ghostscript is invalid.")
      return
    if not os.path.exists(pstoedit):
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The path provided for pstoedit is invalid.")
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



  #
  # main program
  #

  import graphtec
  import pic
  import optimize

  g = graphtec.graphtec()

  g.start()

  border = cnf["border"]
  g.set(offset=(cnf["offset"][0]+border[0]+0.5,cnf["offset"][1]+border[1]+0.5), matrix=cnf["matrix"])
  strokes = pic.read_pic(temp_pic)
  max_x,max_y = optimize.max_extent(strokes)

  tx,ty = 0.5,0.5

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
    tkinter.messagebox.showinfo("G2G_GUI Message", "File '%s' created"  % (Output_name.get()) )


def Just_Exit():
    top.destroy()


def Send_to_Cutter():
    updateConfigDict()
    if not cnf["outputPath"]:
      get_output_filename()
    if not cnf["outputPath"]:
      return
    src=os.path.normpath(cnf["outputPath"])

    if cnf["deviceName"] == "":
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The name of the cutter (as a shared printer) was not provided.")
      return

    if not os.path.isfile(src):
      tkinter.messagebox.showerror("G2G_GUI ERROR", "The Graphtec output file has not been generated, please press the 'Create Graphtec File' button first.")
      return

    #if not os.path.exists(cnf["deviceName"]):
    #  tkinter.messagebox.showerror("G2G_GUI ERROR", "The name of the cutter (as a shared printer) does not exist.")
    #  return

    dst = os.path.normpath(cnf["deviceName"])
    try:
      with open(src, 'r') as f, open(dst, 'w') as lpt:
        while True:
          buf = f.read()
          if not buf: break
          lpt.write(buf)
    except:
      tkinter.messagebox.showerror("G2G_GUI ERROR", "There was an error sending the Graphtec file to the plotter")
      return

#    if os.name=='nt':
#      os.system("copy /B \"%s\" \"%s\"" % (src, dst))
#    else:
#      os.system("cat %s > %s" % (src, dst))

def get_input_filename():
    input_filename=tkinter.filedialog.askopenfilename(title='Select paste mask Gerber file', filetypes=[('Gerber File', ('*.g*', '*.G*')),("All files", "*.*")])
    if input_filename:
        Gerber_name.set(input_filename)

def get_output_filename():
    output_filename=tkinter.filedialog.asksaveasfilename(title='Select output filename', filetypes=[('Output files', '*.txt'),("All files", "*.*")] )
    if output_filename:
        Output_name.set(output_filename)

def get_gerbv_path():
    gerbv_filename=tkinter.filedialog.askopenfilename(title='Select gerbv program', initialfile='gerbv.exe', filetypes=[('Programs', '*.exe')] )
    if gerbv_filename:
        gerbv_path.set(gerbv_filename)

def get_pstoedit_path():
    pstoedit_filename=tkinter.filedialog.askopenfilename(title='Select gerbv program', initialfile='pstoedit.exe', filetypes=[('Programs', '*.exe')] )
    if pstoedit_filename:
        pstoedit_path.set(pstoedit_filename)

def get_ghostscript_path():
    ghostscript_filename=tkinter.filedialog.askopenfilename(title='Select Ghostscript program', initialfile='ghostscript.exe', filetypes=[('Programs', '*.exe')] )
    if ghostscript_filename:
        ghostscript_path.set(ghostscript_filename)

def arrToStr(a):
    return str(a).strip("[]").replace(" ", "")

def getDefaultValue(key, textfieldStr):
    defaultValue = config.getDefaultConfig()[key]
    textfieldStr.set(arrToStr(defaultValue))


Label(top, text="Gerber File ").grid(row=1, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=Gerber_name).grid(row=1, column=1)
tkinter.Button(top, width=9, text = "Browse", command = get_input_filename).grid(row=1, column=2)

Label(top, text="Output File ").grid(row=2, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=Output_name).grid(row=2, column=1)
tkinter.Button(top, width=9, text = "Browse", command = get_output_filename).grid(row=2, column=2)

if os.name=='nt':
  Label(top, text="gerbv path ").grid(row=3, column=0, sticky=W)
  Entry(top, bd =1, width=60, textvariable=gerbv_path).grid(row=3, column=1)
  tkinter.Button(top, width=9, text = "Browse", command = get_gerbv_path).grid(row=3, column=2)

  Label(top, text="Ghostscript path ").grid(row=4, column=0, sticky=W)
  Entry(top, bd =1, width=60, textvariable=ghostscript_path).grid(row=4, column=1)
  tkinter.Button(top, width=9, text = "Browse", command = get_ghostscript_path).grid(row=4, column=2)

  Label(top, text="pstoedit path ").grid(row=5, column=0, sticky=W)
  Entry(top, bd =1, width=60, textvariable=pstoedit_path).grid(row=5, column=1)
  tkinter.Button(top, width=9, text = "Browse", command = get_pstoedit_path).grid(row=5, column=2)

Label(top, text="Offset ").grid(row=6, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=offset_str).grid(row=6, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("offset", offset_str)).grid(row=6, column=2)

Label(top, text="Border ").grid(row=7, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=border_str).grid(row=7, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("border", border_str)).grid(row=7, column=2)

Label(top, text="Matrix ").grid(row=8, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=matrix_str).grid(row=8, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("matrix", matrix_str)).grid(row=8, column=2)

Label(top, text="Speed ").grid(row=9, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=speed_str).grid(row=9, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("speed", speed_str)).grid(row=9, column=2)

Label(top, text="Force ").grid(row=10, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=force_str).grid(row=10, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("force", force_str)).grid(row=10, column=2)

Label(top, text="Cut Mode ").grid(row=11, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=cut_mode_str).grid(row=11, column=1)
tkinter.Button(top, width=9, text = "Default", command = lambda: getDefaultValue("cutMode", cut_mode_str)).grid(row=11, column=2)

if os.name=='nt':
  Label(top, text="Cutter Shared Name").grid(row=12, column=0, sticky=W)
else:
  Label(top, text="Cutter Device Name").grid(row=12, column=0, sticky=W)
Entry(top, bd =1, width=60, textvariable=cutter_shared_name_str).grid(row=12, column=1, sticky=E)

tkinter.Button(top, width=40, text = "Show Gerber", command=show_gerber).grid(row=13, column=1)
tkinter.Button(top, width=40, text = "Create Graphtec File from input", command = main_program).grid(row=14, column=1)
tkinter.Button(top, width=40, text = "Send Graphtec File to Silhouette Cutter", command = Send_to_Cutter).grid(row=15, column=1)
tkinter.Button(top, width=40, text = "Save Configuration", command = saveConfig).grid(row=16, column=1)
tkinter.Button(top, width=40, text = "Exit", command = Just_Exit).grid(row=17, column=1)
tkinter.Button(top, width=40, text = "Create force testing Graphtec file", command=test_forces).grid(row=18, column=1)


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


Gerber_name.set(cnf["inputPath"])
Output_name.set(cnf["outputPath"])
gerbv_path.set(cnf["gerbvPath"])
ghostscript_path.set(cnf["ghostscriptPath"])
pstoedit_path.set(cnf["pstoeditPath"])
offset_str.set(arrToStr(cnf["offset"]))
border_str.set(arrToStr(cnf["border"]))
matrix_str.set(arrToStr(cnf["matrix"]))
speed_str.set(arrToStr(cnf["speed"]))
force_str.set(arrToStr(cnf["force"]))
cut_mode_str.set(cnf["cutMode"])
cutter_shared_name_str.set(cnf["deviceName"])

top.mainloop()
