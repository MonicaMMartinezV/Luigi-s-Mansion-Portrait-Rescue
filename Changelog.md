## [Pre-release-0.0.1] - 08/11/2024

### Added

* Added folder structure for Unity (08/11/2024)
* Added Luigi Prefab (08/11/2024)
* Added Ghost Prefab (09/11/2024)
* Added Boo Prefab (09/11/2024)
* Merge branch develop to Pre-release-0.0.1 (09/11/2024)
* Added initialization of model for test purposes (11/11/2024)
* Added Portrait prefab (11/11/2024)
* Added Portrait Iterations (11/11/2024)
* Added Layout TXT File (19/11/2024)
* Added Door and Wall Prefab (19/11/2024)
* Added and Commented Funtion Grid (19/11/2024)
* Added Function to Receive the File (19/11/2024)
* Added Layout TXT File with Notes (19/11/2024)
* Added new file rescuePortrait (20/11/2024)
* Added new model and agent
* Added basic funtionalities to model and agent (20/11/2024)
* Added funtionalities to model and agent (20/11/2024)
* Added new funtionalities in model (20/11/2024)
* Added new multigrid, process file and funtionalities model (20/11/2024)
* Added server class and funtionality (20/11/2024)
* Added web client file (20/11/2024)
* Added functionality to build board on unity (20/11/2024)
* Added functionality to place initial ghosts on unity (20/11/2024)
* Added functionality to place false alarms and victims on unity (21/11/2024)
* Add functionality to fight fires and smoke (22/11/2024)
* Added TestSeeds.py wrapper to test specific functionalities (22/11/2024)
* Added all funtionalities of explosions, spread_boos and damage to the mansion (24/11/2024)
* Added funtionality respawn POIs and smoke-fire (24/11/2024)
* Added functionality of erasing walls to place doors in model (24/11/2024)
* Added call to check_collision in move function for agent (24/11/2024)
* Added check for doors as viable paths to check_collision (24/11/2024)
* Added funtionalities of A* and heuritic using manhattan (25/11/2024)
* Added new funtionalities to open, close doors and new funtionalities in check walls and doors (26/11/2024)

### Changed

* Modified Ghost Prefab Colors (09/11/2024)
* Modified Luigi Prefab Import (11/11/2024)
* Modified LuigiAgent to match Ghost/Portrait model logic (11/11/2024)
* Modified MansionModel to match Ghost/Portrait diccionary logic (11/11/2024)
* Modified LuigiAgent to save points and open doors (19/11/2024)
* Modified LuigiAgent to prioritize saving portrait (19/11/2024)
* Moved LuigiAgent to Portrait_Rescue file (19/11/2024)
* Modify Grid Funtion to Show Door and Walls (19/11/2024)
* Modify Txt Function (19/11/2024)
* Modify Name Files Project (19/11/2024)
* Modified references to ghosts/portraits to fit multigrid structure (19/11/2024)
* Modify the mansion model (21/11/2024)
* Modify rotation of the ghost prefab (21/11/2024)
* Modify grid height and width (21/11/2024)
* Modify light setup in Unity (21/11/2024)
* Modify Portrait prefab for spinning effect (21/11/2024)
* Modified movement algorithm to use BFS if Manhattan is blocked (22/11/2024)
* Modified end conditions for simulations (22/11/2024)
* Modified portrait spawning to extinguish fire/smoke if needed (22/11/2024)
* Modified funtionality of spread boos/fire to adequate to the explosion funtionality (24/11/2024)
* Modified fire-starting function to activate after every agent step (25/11/2024)
* Modified funtionalities in A*, heuristic and some other (26/11/2024)


### Deprecated

* Restarted Model and Agent (20/11/2024)

### Fixed

* Fixed Luigi Agent variables (09/11/2024)
* Fixed process_txt function (19/11/2024)
* Fixed reference to name of txt file in process_txt function (19/11/2024)
* Fixed points-check conditions in movement functions (22/11/2024)
* Fixed add_portrait method of counting active points of interest (22/11/2024)
* Fixed portraits location in Unity (22/11/2024)
* Fixed coordinate mismatch for fire starting positions (23/11/2024)
* Fixed coordinate for walls and starting positions (23/11/2024)
* Fixed explosions and damage walls (24/11/2024)
* Fixed spawn portraits (24/11/2024)
* Instatite only one wall in Unity (24/11/2024)
* Fixed of movement of firefighter and rescuer (25/11/2024)

### Security

## [develop] - 30/10/2024

### Added

- Created Jupyter Notebook (30/10/2024)
- Added neccesary libraries (30/10/2024)
- Added Luigi and Mansion classes (30/10/2024)
- Created Portrait Rescue Jupyter Notebook (07/11/2024)
- Added GhostAgentFunction (04/11/2024)
- Added Unity Project structure (08/11/2024)

### Changed

* Changed libraries importation (30/10/2024)
* Added funcitionalities to LuigiAgent, GreenGhostAgent,RedGhostAgent and MansionModel(04/11/2024)
* Added functionalities to PortraitAgent(04/11/2024)
* Changed Luigi Model (04/11/2024)
* Added conditions to only absorb red ghosts (04/11/2024)
* Moved ghosts and portraits to MansionModel (05/11/2024)
* Added new libraries (9/11/2024)
* Added commented functionality libraries (11/9/2024)

### Deprecated

### Removed

### Fixed

* Changed artefact to portrait (04/11/2024)
* Fixed agent declaration (04/11/2024)
* Fixed call to artefact instead of portrait (04/11/2024)

### Security
