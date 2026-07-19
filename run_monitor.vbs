' Zapuskaet run_monitor.bat polnostyu skryto (bez okna konsoli).
' Papku vychislyaem vo vremya vypolneniya, chtoby v faile ne bylo kirillicy.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """" & scriptDir & "\" & "run_monitor.bat""", 0, False
