## DrSync

![DrSync Logo](https://raw.githubusercontent.com/spywhere/spywhere.github.com/master/images/drsync/DrSyncMini.png)

A Sublime Text 3 Plugin for settings synchronization on Dropbox and GoogleDrive

### Cloud Service Support Status

Dropbox Status: Working<br />
GoogleDrive Status: Working

Existing user? No problem, you can use Dropbox as a cloud service right away!

### How to use
Open Command Palette then type `Synchronize Settings`, follow the instructions and DrSync will do the rest for you.

\* DrSync version 0.1.3 will use Dropbox as default cloud service. Earlier version will use GoogleDrive instead.

### How to use (complete edition)

 1. Open Command Palette
 * Type `DrSync: Synchronize Settings` (or whatever that select it)
 * Copy a link inside an input panel and open it in browser
 * Allow DrSync to access its AppData folder and retrieve a code
 * Paste it inside that input panel and press `Enter/Return`
 * DrSync will start synchronize your settings
 * If existing synchronization is found, you can select to `Sync To` or `Sync From`

**Note!** While DrSync is running, do not close the Sublime Text until it finished. Otherwise, you will need to synchronize settings all over again.

### Something you may want to know
Always adjust your synchronization preferences before synchronize to cloud service but it is not neccessary when synchronize from cloud service. Since, DrSync keep all synchronization preferences in cloud service too.

While DrSync is synchronize your settings from cloud service, do not try to edit or move any file that DrSync might synchronize such as preferences files or plugins. If any interruption occurred while synchronizing, DrSync will stop and you will need to start over again.

Please report any issue you found, this helps DrSync development get better and less bugs.

### License
	::DrSync::

	urllib3 is included within DrSync packages. License can be found in urllib3 directory.

	The MIT License (MIT)

	Copyright (c) 2014 Sirisak Lueangsaksri

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in all
	copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
	SOFTWARE.
