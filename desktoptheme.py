#!/usr/bin/python3

import configparser # Python 3 only
import sys, os
import glob
import time
import shutil


class Point:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def __str__(self):
		return '{},{}'.format(self.x, self.y)


# KDE rc files differences:
#     Keys are cAsE sensitive
#     No spaces around the =
#     [Sections can have spaces and : colons]
# Also (NOT FIXED):
#     Can have [Sub][Sections]
class KdeConfig(configparser.ConfigParser):
	def __init__(self, filename):
		super().__init__()

		# Keep case sensitive keys
		# http://stackoverflow.com/questions/19359556/configparser-reads-capital-keys-and-make-them-lower-case
		self.optionxform = str

		self.filename = filename
		self.read(self.filename)

	def set(self, section, option, value):
		if not self.has_section(section):
			self.add_section(section)
		super().set(section, option, str(value))

	def setProp(self, key, value):
		section, option = key.split('.', 1)
		return self.set(section, option, value)

	def getProp(self, key):
		section, option = key.split('.', 1)
		return self.get(section, option)

	def default(self, section, option, value):
		if not self.has_option(section, option):
			self.set(section, option, value)

	def save(self):	
		with open(self.filename, 'w') as fp:
			self.write(fp, space_around_delimiters=False)

def limit(minVal, val, maxVal):
	return min(max(minVal, val), maxVal)

def limitColor(val):
	return limit(0, val, 255)

def deltaColor(colorStr, delta):
	r, g, b = map(int, colorStr.split(','))
	if max(r, g, b) >= 128:
		d = -delta
	else:
		d = delta
	return '{},{},{}'.format(limitColor(r+d), limitColor(g+d), limitColor(b+d))

def hoverEffect(colorStr, rd, gd, bd):
	def f(a, b):
		if a + b > 255:
			return limitColor(a - b)
		else:
			return limitColor(a + b)
	r, g, b = map(int, colorStr.split(','))
	return '{},{},{}'.format(f(r, rd), f(g, gd), f(b, bd))

def setTitlebarColors(backgroundColor='0,0,0', textColor='255,255,255'):
	filename = os.path.abspath(os.path.expanduser('~/.config/kdeglobals'))
	kdeglobals = KdeConfig(filename)
	kdeglobals['WM']['activeBackground'] = backgroundColor
	kdeglobals['WM']['inactiveBackground'] = backgroundColor
	kdeglobals['WM']['frame'] = backgroundColor
	kdeglobals['WM']['inactiveFrame'] = backgroundColor
	kdeglobals['WM']['activeForeground'] = textColor
	kdeglobals['WM']['inactiveForeground'] = textColor
	kdeglobals.save()

def applyColorSchemeTitlebarColors(kdeglobals, colorScheme):
	# Default to Breeze.colors if the file leaves it undefined.
	activeBackgroundColor = colorScheme['Colors:Window'].get('BackgroundNormal', '239,240,241')
	kdeglobals['WM']['activeBackground'] = colorScheme['WM'].get('activeBackground', '71,80,87') 
	kdeglobals['WM']['inactiveBackground'] = colorScheme['WM'].get('inactiveBackground', '239,240,241')
	kdeglobals['WM']['frame'] = colorScheme['WM'].get('frame', activeBackgroundColor)
	kdeglobals['WM']['inactiveFrame'] = colorScheme['WM'].get('inactiveFrame', kdeglobals['WM']['frame'])
	kdeglobals['WM']['activeForeground'] = colorScheme['WM'].get('activeForeground', '252,252,252')
	kdeglobals['WM']['inactiveForeground'] = colorScheme['WM'].get('inactiveForeground', '189,195,199')
	kdeglobals.save()



def scanForColorScheme(colorSchemeName):
	def testColorSchemeName(colorScheme, colorSchemeName):
		return colorScheme['General'].get('Name', '') == colorSchemeName

	def scanColorSchemeDir(colorSchemeDir):	
		colorSchemeFilename = colorSchemeName + '.colors'
		dirFilenames = os.listdir(colorSchemeDir)

		# First check to see if the obvious filename exists.
		if colorSchemeFilename in dirFilenames:
			# If so, move it to the front.
			dirFilenames.insert(0, dirFilenames.pop(dirFilenames.index(colorSchemeFilename)))

		# Scan folder for the correct color scheme
		for filename in os.listdir(colorSchemeDir):
			colorSchemeFilepath = os.path.join(colorSchemeDir, filename)
			# print(colorSchemeFilepath)

			if not filename.endswith('.colors'):
				continue

			if not os.path.isfile(colorSchemeFilepath):
				continue

			colorScheme = KdeConfig(colorSchemeFilepath)
			if testColorSchemeName(colorScheme, colorSchemeName):
				return colorScheme

		# Color scheme was not found in this dir
		return None


	# 1st: Check the home color-scheme dir (downloads by the user).
	homeColorSchemeFilepath = os.path.abspath(os.path.expanduser('~/.local/share/color-schemes/'))
	colorScheme = scanColorSchemeDir(homeColorSchemeFilepath)
	if colorScheme:
		return colorScheme

	# 2nd: Check the root color-scheme dir.
	colorScheme = scanColorSchemeDir('/usr/share/color-schemes/')
	if colorScheme:
		return colorScheme

	# No color scheme fulfulled the conditions anywhere
	return None

def resetTitlebarColors():
	kdeglobalsFilename = os.path.abspath(os.path.expanduser('~/.config/kdeglobals'))
	kdeglobals = KdeConfig(kdeglobalsFilename)

	colorSchemeName = kdeglobals['General'].get('ColorScheme', 'Breeze')

	colorScheme = scanForColorScheme(colorSchemeName)
	if colorScheme:
		applyColorSchemeTitlebarColors(kdeglobals, colorScheme)

	# elif os.path.isfile(localDesktopThemeFilename):
	# elif os.path.isfile(rootDesktopThemeFilename):
		# The color scheme is probably in a desktop theme folder...
		# Whatever, user can reapply it.
	else:
		# Deleting the keys will use white + highlight color,
		# which isn't the same as the default Breeze colors.
		del kdeglobals['WM']['activeBackground']
		del kdeglobals['WM']['inactiveBackground']
		del kdeglobals['WM']['frame']
		del kdeglobals['WM']['inactiveFrame']
		del kdeglobals['WM']['activeForeground']
		del kdeglobals['WM']['inactiveForeground']
		kdeglobals.save()

class DesktopTheme:
	def __init__(self, themeName):
		self.themeName = themeName
		themeDir = os.path.abspath(os.path.expanduser('~/.local/share/plasma/desktoptheme'))
		self.themeDir = os.path.join(themeDir, themeName)
		self.dontReload = False

	def colorsConfig(self):
		filename = os.path.join(self.themeDir, 'colors')
		return KdeConfig(filename)

	def reloadTheme(self):
		if self.dontReload:
			# We're setting multiple properties at once,
			# and want to skip automatically reloading
			# after each change.
			return

		# Switch to another theme and back to apply the changes to breeze-alphablack.
		filename = os.path.abspath(os.path.expanduser('~/.config/plasmarc'))
		plasmarc = KdeConfig(filename)

		# Make sure we're not already in the process of changing the theme.
		if plasmarc['Theme']['name'] == self.themeName:
			plasmarc['Theme']['name'] = 'breeze-dark'
			plasmarc.save()
			time.sleep(1)
		plasmarc['Theme']['name'] = self.themeName
		plasmarc.save()

	def clearCache(self):
		wildcardPath='plasma-svgelements-{}_*'.format(self.themeName)
		cacheDir = os.path.realpath(os.path.expanduser('~/.cache/'))
		for file in glob.glob(os.path.join(cacheDir, wildcardPath)):
			print('Deleting cached theme file "{}"'.format(file))
			os.remove(file)

		wildcardPath='plasma_theme_{}_*.kcache'.format(self.themeName)
		for file in glob.glob(os.path.join(cacheDir, wildcardPath)):
			print('Deleting cached theme file "{}"'.format(file))
			os.remove(file)



class BreezeAlphaBlack(DesktopTheme):
	def __init__(self, themeName='breeze-alphablack'):
		super().__init__(themeName=themeName)
		self.configProps = [
			# (group, key, defaultValue, setterKey)
			('dialog', 'opacity', 0.9, 'setDialogOpacity'),
			('dialog', 'padding', 6, 'setDialogPadding'),
			('dialog', 'radius', 3, 'setDialogRadius'),
			('panel', 'opacity', 0.9, 'setPanelOpacity'),
			('panel', 'padding', 2, 'setPanelPadding'),
			('panel', 'taskStyle', 'inside', 'setTasksSvg'),
			('theme', 'accentColor', '0,0,0', 'setAccentColor'),
			('theme', 'highlightColor', '61,174,230', 'setHighlightColor'),
			('theme', 'textColor', '239,240,241', 'setTextColor'),
			('widget', 'opacity', 0.9, 'setWidgetOpacity'),
		]

	def themeConfig(self):
		filename = os.path.join(self.themeDir, 'config.ini')
		config = KdeConfig(filename)
		for (group, key, value, setterKey) in self.configProps:
			config.default(group, key, value)
		return config

	def configGet(self, propPath):
		config = self.themeConfig()
		value = config.getProp(propPath)
		return value

	def configSet(self, propPath, value):
		group1, key1 = propPath.split('.')
		for (group2, key2, defaultValue, setterKey) in self.configProps:
			if group1 == group2 and key1 == key2:
				setter = getattr(self, setterKey)
				setter(value)
				break

	def useTemplate(self, inPath, outPath):
		templatePath = os.path.join(self.themeDir, '_templates', inPath)
		outPath = os.path.join(self.themeDir, outPath)
		shutil.copyfile(templatePath, outPath)
		self.reloadTheme()

	def renderTemplate(self, templatePath, **kwargs):
		inFilename = os.path.join(self.themeDir, '_templates', templatePath)
		outFilename = os.path.join(self.themeDir, templatePath)
		outDir = os.path.dirname(outFilename)
		os.makedirs(outDir, exist_ok=True)
		with open(inFilename, 'r') as fin:
			with open(outFilename, 'w') as fout:
				for line in fin:
					for a, b in kwargs.items():
						line = line.replace(a, b)
					fout.write(line)

	def getDialogPadding(self, config):
		# Plasma doesn't like a padding of 0, so just use a really small number (which is rounded to 0).
		dialogPadding = float(config.getProp('dialog.padding'))
		dialogPadding = max(0.001, dialogPadding)
		return dialogPadding

	def getDialogRadius(self, config):
		# It'd be a pain to adjust the paths to be perfectly square edge, so just do a really small radius.
		dialogRadius = float(config.getProp('dialog.radius'))
		dialogRadius = max(0.001, dialogRadius)
		return dialogRadius

	def calcCorners(self, config):
		out = {}

		dialogPadding = self.getDialogPadding(config)
		out['{{padding}}'] = str(dialogPadding)

		centerSize = 32
		dialogRadius = self.getDialogRadius(config) # Default = 3
		size = dialogRadius # max(6, dialogRadius) # Default = 6
		extra = size - dialogRadius # Default = 3
		farEdgeOffset = size + centerSize # Default = 38
		marginThickness = 4 # This is just a visual cue
		marginCenterOffset = size + (centerSize/2) - (marginThickness/2) # Default = 20
		marginFarOffset = size + centerSize + size - dialogPadding

		out['{{centerSize}}'] = str(centerSize)
		out['{{edgeSize}}'] = str(size)
		out['{{extraSize}}'] = str(extra)
		out['{{farEdgeOffset}}'] = str(farEdgeOffset)
		out['{{marginThickness}}'] = str(marginThickness)
		out['{{marginCenterOffset}}'] = str(marginCenterOffset)
		out['{{marginFarOffset}}'] = str(marginFarOffset)

		third = dialogRadius * 1/3
		twoThird = dialogRadius * 2/3

		#--- Background+Mask Tileset
		# topLeft (Clockwise)
		# m 6,6 h -6 v -3 c 0,-2 1,-3 3,-3 h 3 z
		path = 'm {} h {} v {} c {} {} {} h {} z'.format(
			# m
			Point(size, size), # point touching center
			# h 
			-size,
			# v
			-extra,
			# c
			Point(0, -twoThird),
			Point(third, -dialogRadius),
			Point(dialogRadius, -dialogRadius),
			# h
			extra,
			# z
		)
		out['{{topLeftPath}}'] = path

		# topRight (Clockwise)
		# m 38,6 v -6 h 3 c 2,0 3,1 3,3 v 3 z
		path = 'm {} v {} h {} c {} {} {} v {} z'.format(
			# m
			Point(farEdgeOffset, size), # point touching center
			# v 
			-size,
			# h
			extra,
			# c
			Point(twoThird, 0),
			Point(dialogRadius, third),
			Point(dialogRadius, dialogRadius),
			# v
			extra,
			# z
		)
		out['{{topRightPath}}'] = path

		# bottomLeft (Clockwise)
		# m 6,38 v 6 h -3 c -2,0 -3,-1 -3,-3 v -3 z
		path = 'm {} v {} h {} c {} {} {} v {} z'.format(
			# m
			Point(size, farEdgeOffset), # point touching center
			# v 
			size,
			# h
			-extra,
			# c
			Point(-twoThird, 0),
			Point(-dialogRadius, -third),
			Point(-dialogRadius, -dialogRadius),
			# v
			-extra,
			# z
		)
		out['{{bottomLeftPath}}'] = path

		# bottomRight (Clockwise)
		# m 38,38 h 6 v 3 c 0,2 -1,3 -3,3 h -3 z
		path = 'm {} h {} v {} c {} {} {} h {} z'.format(
			# m
			Point(farEdgeOffset, farEdgeOffset), # point touching center
			# h
			size,
			# v
			extra,
			# c
			Point(0, twoThird),
			Point(-third, dialogRadius),
			Point(-dialogRadius, dialogRadius),
			# h
			-extra,
			# z
		)
		out['{{bottomRightPath}}'] = path

		#--- Shadow Tileset
		shadowSize = 6
		out['{{shadowSize}}'] = str(shadowSize)

		shadowAndRadius = shadowSize + dialogRadius # Default = 9
		shadowEdgeSize = shadowSize + size # Default = 12
		shadowFarEdge = shadowEdgeSize + centerSize # Default = 44
		shadowFarShadow = shadowEdgeSize + centerSize + size # Default = 50
		shadowTilesetSize = shadowEdgeSize + centerSize + shadowEdgeSize # Default = 56
		out['{{shadowAndRadius}}'] = str(shadowAndRadius)
		out['{{shadowEdgeSize}}'] = str(shadowEdgeSize)
		out['{{shadowFarEdge}}'] = str(shadowFarEdge)
		out['{{shadowFarShadow}}'] = str(shadowFarShadow)
		out['{{shadowTilesetSize}}'] = str(shadowTilesetSize)

		edgeStopDone = 2/3 # Default = 0.66
		cornerStopA = size / shadowEdgeSize # Default = 0.33
		cornerStopB = (size + shadowSize*edgeStopDone) / shadowEdgeSize # Default = 0.77
		out['{{edgeStopDone}}'] = str(edgeStopDone)
		out['{{cornerStopA}}'] = str(cornerStopA)
		out['{{cornerStopB}}'] = str(cornerStopB)

		# shadowTopLeft (CounterClockwise)
		# m 0,0 v 9 h 6 c 0,-2 1,-3 3,-3 v -6 z
		path = 'm {} v {} h {} c {} {} {} v {} z'.format(
			# m
			Point(0, 0), # point furthest from center
			# v
			shadowAndRadius,
			# h
			shadowSize,
			# c
			Point(0, -twoThird),
			Point(third, -dialogRadius),
			Point(dialogRadius, -dialogRadius),
			# v
			-shadowSize,
			# z
		)
		out['{{shadowTopLeftPath}}'] = path

		# shadowTopRight (CounterClockwise)
		# m 56,0 h -9 v 6 c 2,0 3,1 3,3 h 6 z
		path = 'm {} h {} v {} c {} {} {} h {} z'.format(
			# m
			Point(shadowTilesetSize, 0), # point furthest from center
			# h
			-shadowAndRadius,
			# v
			shadowSize,
			# c
			Point(twoThird, 0),
			Point(dialogRadius, third),
			Point(dialogRadius, dialogRadius),
			# h
			shadowSize,
			# z
		)
		out['{{shadowTopRightPath}}'] = path

		# shadowBottomLeft (CounterClockwise)
		# m 0,56 h 9 v -6 c -2,0 -3,-1 -3,-3 h -6 z
		path = 'm {} h {} v {} c {} {} {} h {} z'.format(
			# m
			Point(0, shadowTilesetSize), # point furthest from center
			# h
			shadowAndRadius,
			# v
			-shadowSize,
			# c
			Point(-twoThird, 0),
			Point(-dialogRadius, -third),
			Point(-dialogRadius, -dialogRadius),
			# h
			-shadowSize,
			# z
		)
		out['{{shadowBottomLeftPath}}'] = path

		# shadowBottomRight (CounterClockwise)
		# m 56,56 v -9 h -6 c 0,2 -1,3 -3,3 v 6 z
		path = 'm {} v {} h {} c {} {} {} v {} z'.format(
			# m
			Point(shadowTilesetSize, shadowTilesetSize), # point furthest from center
			# v
			-shadowAndRadius,
			# h
			-shadowSize,
			# c
			Point(0, twoThird),
			Point(-third, dialogRadius),
			Point(-dialogRadius, dialogRadius),
			# v
			shadowSize,
			# z
		)
		out['{{shadowBottomRightPath}}'] = path

		return out

	def getDialogVars(self, config):
		dialogVars = {
			'{{fillOpacity}}': str(config.getProp('dialog.opacity')),
		}
		cornerVars = self.calcCorners(config)
		dialogVars.update(cornerVars)
		return dialogVars

	def renderDialogBackground(self, config):
		dialogVars = self.getDialogVars(config)

		from pprint import pprint
		pprint(dialogVars)

		self.renderTemplate('dialogs/background.svg', **dialogVars)

	def renderPlasmoidHeading(self, config):
		dialogVars = self.getDialogVars(config)
		self.renderTemplate('widgets/plasmoidheading.svg', **dialogVars)

	def setDialogProperty(self, key, newValue):
		config = self.themeConfig()
		config.set('dialog', key, newValue)
		self.renderDialogBackground(config)
		self.renderPlasmoidHeading(config)
		config.save()
		self.clearCache() # Not really necessary
		self.reloadTheme()

	def setDialogOpacity(self, newOpacity=0.9):
		self.setDialogProperty('opacity', newOpacity)

	def setDialogPadding(self, newPadding=6):
		self.setDialogProperty('padding', newPadding)

	def setDialogRadius(self, newRadius=3):
		self.setDialogProperty('radius', newRadius)

	def renderPanel(self, config):
		# inFilename = os.path.join(self.themeDir, '_templates/panel-background.svg')
		# outFilename = os.path.join(self.themeDir, 'widgets/panel-background.svgz')
		# buildFromTemplate(inFilename, outFilename, **{
		panelOpacity = config.getProp('panel.opacity')
		noPanelPadding = config.getint('panel', 'padding') == 0
		shadowOpacity = 1 if float(panelOpacity) >= 0.3 else 0
		self.renderTemplate('widgets/panel-background.svg', **{
			'{{panelOpacity}}': str(panelOpacity),
			'{{panelPadding}}': str(config.getProp('panel.padding')),
			'{{noPanelPadding}}': '<rect id="hint-no-border-padding"></rect>' if noPanelPadding else '',
			'{{shadowOpacity}}': str(shadowOpacity),
		})
		print('noPanelPadding', noPanelPadding)
		print('shadowOpacity', shadowOpacity)

	def setPanelOpacity(self, newOpacity=0.9):
		config = self.themeConfig()
		config.set('panel', 'opacity', newOpacity)
		self.renderPanel(config)
		config.save()
		self.clearCache() # Not really necessary
		self.reloadTheme()

	def setPanelPadding(self, newPadding=2):
		config = self.themeConfig()
		config.set('panel', 'padding', newPadding)
		self.renderPanel(config)
		config.save()
		self.clearCache() # Necessary
		self.reloadTheme()

	def renderWidgetBackground(self, config):
		# Breeze's widget/background.svg
		# fill: 0.9
		# shadows: 1.0 (Linear gradients)
		# corner shadows: 0.6 (Radial gradients)
		fillOpacity = float(config.getProp('widget.opacity'))
		if fillOpacity == 0:
			# Hide shadows completely if there's no fill
			shadowOpacity = 0
			cornerOpacity = 0
		else:
			shadowOpacity = min(fillOpacity + 0.1, 1)
			cornerOpacity = 0.6 * shadowOpacity
		
		self.renderTemplate('widgets/background.svg', **{
			'{{fillOpacity}}': str(fillOpacity),
			'{{shadowOpacity}}': str(shadowOpacity),
			'{{cornerOpacity}}': str(cornerOpacity),
		})

	def setWidgetOpacity(self, newOpacity=0.9):
		config = self.themeConfig()
		config.set('widget', 'opacity', newOpacity)
		self.renderWidgetBackground(config)
		config.save()
		self.clearCache() # Not really necessary
		self.reloadTheme()

	def _applyColors(self, accentColor='0,0,0', textColor='239,240,241', highlightColor='61,174,230'):
		altColor = deltaColor(accentColor, 23)
		compColor = deltaColor(accentColor, 17)
		compFocusColor = hoverEffect(highlightColor, -31, -28, 25) # 61,174,230 => 30,146,255
		focusColor = highlightColor
		hoverColor = highlightColor
		selectionColor = highlightColor
		selectionAltColor = hoverEffect(selectionColor, -13, -36, -47) # 61,174,230 => 48,138,183

		print('BackgroundNormal: {}'.format(accentColor))
		print('BackgroundAlternate: {}'.format(altColor))
		print('Complementary.BackgroundNormal: {}'.format(compColor))
		print('Complementary.DecorationFocus: {}'.format(compFocusColor))
		print('DecorationFocus: {}'.format(focusColor))
		print('DecorationHover: {}'.format(hoverColor))
		print('Selection.BackgroundNormal: {}'.format(selectionColor))
		print('Selection.BackgroundAlternate: {}'.format(selectionAltColor))

		setTitlebarColors(accentColor, textColor)

		colors = self.colorsConfig()
		allColorGroups = [
			'Colors:Button',
			'Colors:Selection',
			'Colors:Tooltip',
			'Colors:View',
			'Colors:Window',
			'Colors:Complementary',
			'Colors:Header',
		]
		allButComplementaryGroup = [g for g in allColorGroups if g != 'Colors:Complementary']
		def applyToGroups(groups, key, value):
			for group in groups:
				colors[group][key] = value

		colors['Colors:Button']['BackgroundNormal'] = compColor
		colors['Colors:Button']['BackgroundAlternate'] = altColor
		colors['Colors:Button']['ForegroundNormal'] = textColor
		colors['Colors:Header']['BackgroundNormal'] = accentColor
		colors['Colors:Header']['BackgroundAlternate'] = altColor
		colors['Colors:Header']['ForegroundNormal'] = textColor
		colors['Colors:View']['BackgroundNormal'] = accentColor
		colors['Colors:View']['BackgroundAlternate'] = altColor
		colors['Colors:View']['ForegroundNormal'] = textColor
		colors['Colors:Window']['BackgroundNormal'] = accentColor
		colors['Colors:Window']['BackgroundAlternate'] = altColor
		colors['Colors:Window']['ForegroundNormal'] = textColor
		colors['Colors:Complementary']['BackgroundNormal'] = compColor
		colors['Colors:Complementary']['BackgroundAlternate'] = altColor
		colors['Colors:Complementary']['ForegroundNormal'] = textColor

		# Focus
		applyToGroups(allButComplementaryGroup, 'DecorationFocus', focusColor)
		colors['Colors:Complementary']['DecorationFocus'] = compFocusColor

		# Hover
		applyToGroups(allColorGroups, 'DecorationHover', hoverColor)
		colors['Colors:Selection']['BackgroundNormal'] = selectionColor # Note this variable controls `theme.highlightColor`
		colors['Colors:Selection']['BackgroundAlternate'] = selectionAltColor

		colors.save()

		config = self.themeConfig()
		config.set('theme', 'accentColor', accentColor)
		config.set('theme', 'highlightColor', highlightColor)
		config.set('theme', 'textColor', textColor)
		config.save()

		self.reloadTheme()

	def applyColors(self, accentColor=None, textColor=None, highlightColor=None):
		config = self.themeConfig()
		if accentColor is None:
			accentColor = config.get('theme', 'accentColor')
		if textColor is None:
			textColor = config.get('theme', 'textColor')
		if highlightColor is None:
			highlightColor = config.get('theme', 'highlightColor')
		self._applyColors(accentColor, textColor, highlightColor)

	def setAccentColor(self, accentColor):
		self.applyColors(accentColor=accentColor)

	def setHighlightColor(self, highlightColor):
		self.applyColors(highlightColor=highlightColor)

	def setTextColor(self, textColor):
		self.applyColors(textColor=textColor)

	def setTasksSvg(self, taskTheme):
		templatePath = "tasks-{}.svg".format(taskTheme)
		self.useTemplate(templatePath, 'widgets/tasks.svg')

		config = self.themeConfig()
		config.set('panel', 'taskStyle', taskTheme)
		config.save()

		self.reloadTheme()

	def resetToDefaults(self):
		self.dontReload = True
		for (group, key, value, setterKey) in self.configProps:
			print("===[ {}.{}: {} ]===".format(group, key, value))
			setter = getattr(self, setterKey)
			setter(value)

		self.dontReload = False
		self.reloadTheme()




#--- Main
def theme_getall(args):
	import json

	desktoptheme = BreezeAlphaBlack()
	config = desktoptheme.themeConfig()

	if args.json:
		out = {}
		for section in config.sections():
			out[section] = {}
			for name, value in config.items(section):
				out[section][name] = value
		print(json.dumps(out, indent="\t"))
	else:
		for section in config.sections():
			for name, value in config.items(section):
				print("{}.{}: {}".format(section, name, value))

def theme_get(args):
	desktopTheme = BreezeAlphaBlack()
	argsVars = vars(args)
	propPath = argsVars['section.property']
	value = desktopTheme.configGet(propPath)
	print(value)

def theme_set(args):
	desktopTheme = BreezeAlphaBlack()
	config = desktopTheme.themeConfig()
	argsVars = vars(args)
	propPath = argsVars['section.property']
	desktopTheme.configSet(propPath, args.value)


def theme_setTitlebarColors(args):
	def parseColorStr(colorStr):
		r, g, b = map(int, colorStr.split(','))
		return "{},{},{}".format(r, g, b)

	argsVars = vars(args)
	if argsVars.get('bgColor'):
		bgColor = parseColorStr(argsVars.get('bgColor'))
		if argsVars.get('textColor'):
			textColor = parseColorStr(argsVars.get('textColor'))
			setTitlebarColors(bgColor, textColor)
		else:
			setTitlebarColors(bgColor)

def theme_reset(args):
	desktopTheme = BreezeAlphaBlack()
	desktopTheme.resetToDefaults()

def theme_resetTitlebarColors(args):
	resetTitlebarColors()

def main():
	import argparse

	parser = argparse.ArgumentParser(
		prog='desktoptheme',
		description='Python script to modify a desktop theme.',
		epilog='Note that colors must be [red],[green],[blue] (seperated by commas). [red/green/blue] are integers from 0-255.'
	)
	subparsers = parser.add_subparsers()

	def add_subcommand(name, func, *args, description=None):
		tokens = ['[{}]'.format(arg) for arg in args]
		tokens = ['python3', 'desktoptheme.py', name] + tokens
		cmdstr = ' '.join(tokens)
		helpstr = cmdstr
		if description:
			helpstr += ' - ' + description
		parser_subcommand = subparsers.add_parser(name, help=helpstr)
		parser_subcommand.set_defaults(func=func)
		for arg in args:
			parser_subcommand.add_argument(arg)
		return parser_subcommand

	parser_getall = add_subcommand('getall', theme_getall)
	parser_getall.add_argument('--json', default=False, action='store_true')
	add_subcommand('get', theme_get, 'section.property')
	add_subcommand('set', theme_set, 'section.property', 'value')
	add_subcommand('settitlebarcolor', theme_setTitlebarColors, 'bgColor', description='Eg: 0,0,0')
	add_subcommand('settitlebarcolors', theme_setTitlebarColors, 'bgColor', 'textColor', description='Eg: 0,0,0 255,255,255')
	add_subcommand('reset', theme_reset)
	add_subcommand('resettitlebarcolors', theme_resetTitlebarColors)
	

	args = parser.parse_args()

	if 'func' in args:
		try:
			args.func(args)
		except KeyboardInterrupt:
			pass
	else:
		parser.print_help()


if __name__ == '__main__':
	main()
