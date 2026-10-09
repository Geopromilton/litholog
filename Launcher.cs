using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace LithoLogStudio
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
                string venvPythonW = Path.Combine(baseDir, ".venv", "Scripts", "pythonw.exe");
                string pythonExe = File.Exists(venvPython) ? venvPython : (File.Exists(venvPythonW) ? venvPythonW : "python.exe");
                string desktopScript = Path.Combine(baseDir, "litholog", "gui.py");

                if (!File.Exists(desktopScript))
                {
                    MessageBox.Show("Cannot locate litholog\\gui.py in " + baseDir, "LithoLog Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonExe;
                psi.Arguments = string.Format("\"{0}\"", desktopScript);
                psi.WorkingDirectory = baseDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process p = Process.Start(psi);
                if (p != null)
                {
                    p.WaitForExit();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to launch LithoLog Studio: " + ex.Message, "LithoLog Studio Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
