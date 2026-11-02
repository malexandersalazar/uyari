# 0001 One Python package; data in plain folders

The code is one Python package (`src/uyari`) with one CLI (`uyari`), so the same commands run on a Windows
laptop and on the Ubuntu GPU box. Data lives in plain, reviewable folders (`primary/`, `languages/`,
`contributing/`) that contributors edit through pull requests; nothing about a language is in code.
Where a design assumption conflicts with the data that actually exists, the data wins and the change is
recorded in this folder.
