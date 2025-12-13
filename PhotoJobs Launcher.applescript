-- PhotoJobs Launcher (template)
-- Runs from the PhotoJobsTools folder and calls: python3 -m photojobs <command>

set toolsFolder to POSIX path of ((path to me) as text)
set toolsFolder to POSIX path of ((POSIX file toolsFolder) as alias)
set AppleScript's text item delimiters to "/"
set folderParts to text items of toolsFolder
set AppleScript's text item delimiters to "/"
set toolsFolder to (items 1 thru -2 of folderParts) as string
set toolsFolder to "/" & toolsFolder

set taskList to {"Run All", "keywords", "verify", "csvgen", "rename", "teams"}
set chosenTask to choose from list taskList with prompt "Choose PhotoJobs task:" default items {"Run All"}
if chosenTask is false then return
set cmdName to item 1 of chosenTask

-- Common prompts
set csvPath to ""
set rootPath to ""
set outText to ""

if cmdName is "Run All" then
	-- Prompt for initial inputs
	set csvAlias to choose file with prompt "Select the CSV file:" of type {"public.comma-separated-values-text", "public.text"}
	set csvPath to POSIX path of csvAlias
	set rootFolder to choose folder with prompt "Select the ROOT folder that contains the original images (job folder):"
	set rootPath to POSIX path of rootFolder
	set manualKeywordDialog to display dialog "Enter an extra keyword to add to ALL images (leave blank for none):" default answer ""
	set manualKeyword to text returned of manualKeywordDialog

	-- Extract job name from CSV filename
	set AppleScript's text item delimiters to "/"
	set csvFileName to last text item of csvPath
	set AppleScript's text item delimiters to "."
	set jobName to first text item of csvFileName
	set AppleScript's text item delimiters to ""

	-- Detect preset
	set presetName to ""
	try
		set firstLine to do shell script "head -n 1 " & quoted form of csvPath
		if firstLine contains "Access Code" then
			set presetName to "photoday"
		else if firstLine contains "SPA" then
			set presetName to "legacy"
		end if
	end try
	if presetName is "" then
		set presetChoice to choose from list {"photoday", "legacy"} with prompt "Choose preset:" default items {"photoday"}
		if presetChoice is false then return
		set presetName to item 1 of presetChoice
	end if

	-- Derived paths
	set parentFolder to do shell script "dirname " & quoted form of rootPath
	set rootFolderName to do shell script "basename " & quoted form of rootPath
	set keywordsPath to parentFolder & "/" & rootFolderName & "_keywords"
	set renamedPath to parentFolder & "/" & rootFolderName & "_keywords_renamed"
	set csvDir to do shell script "dirname " & quoted form of csvPath
	set jpgCsvPath to csvDir & "/" & jobName & " DATA-JPG.csv"
	set pngCsvPath to csvDir & "/" & jobName & " DATA-PNG.csv"

	-- Progress indicator
	try
		set progress total steps to 4
		set progress completed steps to 0
		set progress description to "Running PhotoJobs: Full Workflow"
	end try

	-- Step 1: Keywords
	try
		set progress additional description to "Step 1/4: Applying keywords..."
	end try

	if manualKeyword is not "" then
		set cmd1 to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --manual " & quoted form of manualKeyword & " --preset " & quoted form of presetName
	else
		set cmd1 to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs keywords --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --preset " & quoted form of presetName
	end if

	set result1 to do shell script cmd1
	try
		set progress completed steps to 1
	end try

	-- Step 2: csvgen
	try
		set progress additional description to "Step 2/4: Generating CSV files..."
	end try

	set cmd2 to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs csvgen --csv " & quoted form of csvPath & " --jobname " & quoted form of jobName
	set result2 to do shell script cmd2
	try
		set progress completed steps to 2
	end try

	-- Step 3: Rename
	try
		set progress additional description to "Step 3/4: Renaming files..."
	end try

	set cmd3 to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs rename --root " & quoted form of keywordsPath & " --plan " & quoted form of jpgCsvPath & " --mode copy"
	set result3 to do shell script cmd3
	try
		set progress completed steps to 3
	end try

	-- Step 4: Teams
	try
		set progress additional description to "Step 4/4: Sorting into teams..."
	end try

	-- Check for multiple batches
	set batchCheckCmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -c \"import csv; f=open('" & pngCsvPath & "'); r=csv.DictReader(f); batches=set(row.get('BATCH','UNKNOWN') for row in r); print(len(batches), ','.join(sorted(batches)))\""
	set batchInfo to do shell script batchCheckCmd
	set AppleScript's text item delimiters to " "
	set batchParts to text items of batchInfo
	set batchCount to item 1 of batchParts as integer
	set AppleScript's text item delimiters to ""

	-- Check if there are people without teams
	set checkCmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -c \"import csv; f=open('" & pngCsvPath & "'); r=csv.DictReader(f); missing=sum(1 for row in r if not row.get('TEAMNAME', '').strip()); print(missing)\""
	set missingCount to do shell script checkCmd

	-- Build input for teams command (may need batch selection and/or default team)
	set teamsInput to ""

	-- Handle batch selection if multiple batches
	if batchCount > 1 then
		set batchDialog to display dialog "Multiple image batches detected in CSV. Which batch should be used for team selection?" & return & return & batchInfo & return & return & "Enter batch number (or 'all' for all batches):" default answer "1"
		set batchChoice to text returned of batchDialog
		set teamsInput to batchChoice & return
	end if

	-- Handle missing team names
	if missingCount as integer > 0 then
		set defaultTeamDialog to display dialog "There are " & missingCount & " people without a team. Enter a default team name for them:" default answer "NoTeam"
		set defaultTeam to text returned of defaultTeamDialog
		set teamsInput to teamsInput & defaultTeam & return
	end if

	-- Run teams command
	if teamsInput is not "" then
		set cmd4 to "cd " & quoted form of toolsFolder & " && echo " & quoted form of teamsInput & " | /usr/bin/python3 -m photojobs teams --csv " & quoted form of pngCsvPath & " --root " & quoted form of renamedPath & " --team-field TEAMNAME"
	else
		set cmd4 to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs teams --csv " & quoted form of pngCsvPath & " --root " & quoted form of renamedPath & " --team-field TEAMNAME"
	end if

	set result4 to do shell script cmd4
	try
		set progress completed steps to 4
	end try

	-- Combine results
	set resultText to "=== STEP 1: KEYWORDS ===" & return & result1 & return & return & "=== STEP 2: CSVGEN ===" & return & result2 & return & return & "=== STEP 3: RENAME ===" & return & result3 & return & return & "=== STEP 4: TEAMS ===" & return & result4
	set summaryText to "Full workflow completed successfully!" & return & return & "Output locations:" & return & "- Keywords: " & keywordsPath & return & "- Renamed: " & renamedPath & return & "- CSV files: " & csvDir & return & "- Teams: " & parentFolder & "/_TeamIndSorted"
	display dialog summaryText buttons {"OK"} default button 1 with title "PhotoJobs: Run All Complete"
	return

else if cmdName is "keywords" then
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
	-- Extract job name from CSV filename (remove extension)
	set AppleScript's text item delimiters to "/"
	set csvFileName to last text item of csvPath
	set AppleScript's text item delimiters to "."
	set jobName to first text item of csvFileName
	set AppleScript's text item delimiters to ""
	set shcmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -m photojobs csvgen --csv " & quoted form of csvPath & " --jobname " & quoted form of jobName
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

	-- Check for multiple batches
	set batchCheckCmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -c \"import csv; f=open('" & csvPath & "'); r=csv.DictReader(f); batches=set(row.get('BATCH','UNKNOWN') for row in r); print(len(batches), ','.join(sorted(batches)))\""
	set batchInfo to do shell script batchCheckCmd
	set AppleScript's text item delimiters to " "
	set batchParts to text items of batchInfo
	set batchCount to item 1 of batchParts as integer
	set AppleScript's text item delimiters to ""

	-- Check if there are people without teams
	set checkCmd to "cd " & quoted form of toolsFolder & " && /usr/bin/python3 -c \"import csv; f=open('" & csvPath & "'); r=csv.DictReader(f); missing=sum(1 for row in r if not row.get('TEAMNAME', '').strip()); print(missing)\""
	set missingCount to do shell script checkCmd

	-- Build input for teams command
	set teamsInput to ""

	-- Handle batch selection if multiple batches
	if batchCount > 1 then
		set batchDialog to display dialog "Multiple image batches detected in CSV. Which batch should be used for team selection?" & return & return & batchInfo & return & return & "Enter batch number (or 'all' for all batches):" default answer "1"
		set batchChoice to text returned of batchDialog
		set teamsInput to batchChoice & return
	end if

	-- Handle missing team names
	if missingCount as integer > 0 then
		set defaultTeamDialog to display dialog "There are " & missingCount & " people without a team. Enter a default team name for them:" default answer "NoTeam"
		set defaultTeam to text returned of defaultTeamDialog
		set teamsInput to teamsInput & defaultTeam & return
	end if

	-- Run teams command
	if teamsInput is not "" then
		set shcmd to "cd " & quoted form of toolsFolder & " && echo " & quoted form of teamsInput & " | /usr/bin/python3 -m photojobs teams --csv " & quoted form of csvPath & " --root " & quoted form of rootPath & " --team-field TEAMNAME"
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
