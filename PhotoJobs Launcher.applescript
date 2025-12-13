-- PhotoJobs Launcher (template)
-- Runs from the PhotoJobsTools folder and calls: python3 -m photojobs <command>

set toolsFolder to POSIX path of ((path to me) as text)
set toolsFolder to POSIX path of ((POSIX file toolsFolder) as alias)
set AppleScript's text item delimiters to "/"
set folderParts to text items of toolsFolder
set AppleScript's text item delimiters to "/"
set toolsFolder to (items 1 thru -2 of folderParts) as string
set toolsFolder to "/" & toolsFolder

set taskList to {"keywords", "verify", "csvgen", "rename", "teams"}
set chosenTask to choose from list taskList with prompt "Choose PhotoJobs task:" default items {"keywords"}
if chosenTask is false then return
set cmdName to item 1 of chosenTask

-- Common prompts
set csvPath to ""
set rootPath to ""
set outText to ""

if cmdName is "keywords" then
	set csvAlias to choose file with prompt "Select the CSV file:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder that contains the original images (job folder):"
	set rootPath to POSIX path of rootFolder
	set manualKeywordDialog to display dialog "Enter an extra keyword to add to ALL images (leave blank for none):" default answer ""
	set manualKeyword to text returned of manualKeywordDialog
	-- Detect preset from Column A header
	set presetName to ""
	try
		set firstLine to do shell script "head -n 1 " & quoted form of csvPath
		if firstLine contains "Access Code" then
			set presetName to "photoday"
		else if firstLine contains "SPA" then
			set presetName to "legacy"
		end if
	end try
	
	-- Fallback to prompt if unknown
	if presetName is "" then
		set presetChoice to choose from list {"photoday", "legacy"} with prompt "Choose preset:" default items {"photoday"}
		if presetChoice is false then return
		set presetName to item 1 of presetChoice
	end if
	if manualKeyword is not "" then
		set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --manual " & quoted form of manualKeyword & " --preset " & quoted form of presetName
	else
		set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --preset " & quoted form of presetName
	end if
else if cmdName is "verify" then
	set rootFolder to choose folder with prompt "Select the SOURCE root folder (job folder):"
	set rootPath to POSIX path of rootFolder
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs verify --root " & quoted form of rootPath
else if cmdName is "csvgen" then
	set csvAlias to choose file with prompt "Select the CSV file:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder containing original images:"
	set rootPath to POSIX path of rootFolder
	-- Extract job name from CSV filename (remove extension)
	set AppleScript's text item delimiters to "/"
	set csvFileName to last text item of csvPath
	set AppleScript's text item delimiters to "."
	set jobName to first text item of csvFileName
	set AppleScript's text item delimiters to ""
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs csvgen --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --jobname " & quoted form of jobName
else if cmdName is "rename" then
	set planAlias to choose file with prompt "Select the RENAME DATA (JPG) file:" of type {"public.text", "public.comma-separated-values-text"}
	set planPath to POSIX path of planAlias
	set rootFolder to choose folder with prompt "Select the IMAGE SOURCE folder (copy mode by default):"
	set rootPath to POSIX path of rootFolder
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs rename --root " & quoted form of rootPath & " --plan " & quoted form of planPath & " --mode copy"
else if cmdName is "teams" then
	set csvAlias to choose file with prompt "Select the PNG CSV file from csvgen:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the folder containing PNG images:"
	set rootPath to POSIX path of rootFolder
	
	-- Check if there are people without teams
	set checkCmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -c \"import csv; f=open('" & csvPath & "'); r=csv.DictReader(f); missing=sum(1 for row in r if not row.get('TEAMNAME', '').strip()); print(missing)\""
	set missingCount to do shell script checkCmd
	
	if missingCount as integer > 0 then
		set defaultTeamDialog to display dialog "There are " & missingCount & " people without a team. Enter a default team name for them:" default answer "NoTeam"
		set defaultTeam to text returned of defaultTeamDialog
		set shcmd to "cd " & quoted form of toolsFolder & " && echo " & quoted form of defaultTeam & " | /usr/bin/python3 -m photojobs teams --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --team-field TEAMNAME"
	else
		set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs teams --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --team-field TEAMNAME"
	end if
end if

-- Progress indicator while running
try
	set progress total steps to 1
	set progress completed steps to 0
	set progress description to "Running PhotoJobs: " & cmdName
	set progress additional description to "Working..."
end try

set resultText to do shell script shcmd

try
	set progress completed steps to 1
end try

-- Extract summary
set AppleScript's text item delimiters to "=== Summary ==="
set parts to text items of resultText
if (count of parts) > 1 then
	set summaryText to "=== Summary ===" & item -1 of parts
else
	set summaryText to resultText
end if
set AppleScript's text item delimiters to ""

display dialog summaryText buttons {"OK"} default button 1 with title "PhotoJobs Results"
