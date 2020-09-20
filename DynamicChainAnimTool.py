# ----------------------------------------------------------------------------------------------------------------------
"""

	DYNAMICCHAINANIMTOOL.PY
	Add dynamics to existing animation using maya nHair.

	Antony Thomas
	antony@thomas-cgi.com

"""
# ----------------------------------------------------------------------------------------------------------------------

from maya.api import OpenMaya as om2
import maya.cmds as cmds


name = "DynChain"


def makeCurvFromPoints(cvs_array, transform_fn=None):
	"""
	Generate a spline from an array of points.
	:param cvs_array:  MPointArray to generate curve from.
	:param transform_fn:  Optional argument for parenting curve under existing transform.
	:return:  TransformFn, NurbsCurveFn
	"""
	knot_vector = om2.MDoubleArray()

	# calculate knot vector
	degree = 2
	nspans = len(cvs_array) - degree
	nknots = nspans + 2 * degree - 1

	for i in range(degree - 1):
		knot_vector.append(0.0)
	for j in range(nknots - (2 * degree) + 2):
		knot_vector.append(j)
	for k in range(degree - 1):
		knot_vector.append(j)

	# create curve
	if transform_fn is None:
		transform_fn = om2.MFnTransform()
		transform_fn.create()
		# transform_fn.setName('%s_input_curv' % name)

	curvFn = om2.MFnNurbsCurve()
	curvFn.create(cvs_array, knot_vector, degree, om2.MFnNurbsCurve.kOpen, False, True, transform_fn.object())

	return transform_fn, curvFn
# end def makeCurvFromPoints():


def iterDagPathFromSelection():
	"""
	Iterator for all the dag nodes in selection.
	:yield:  MDagPath
	"""
	sel = om2.MGlobal.getActiveSelectionList()

	for i in xrange(sel.length()):
		itemMob = sel.getDependNode(i)
		if itemMob.hasFn(om2.MFn.kDagNode):
			yield sel.getDagPath(i)
		else:
			print('//Warning -- skipping selected item: %s. Not a dag node.' %
					(om2.MFnDependencyNode(itemMob).name()))
# end def iterDagPathFromSelection():


def getMObFromStr(str_name):
	"""
	Get MObject from str name.
	:param str_name:  str name.
	:return:  MObject
	"""
	selLs = om2.MSelectionList()
	selLs.add(str_name)

	return selLs.getDependNode(0)
# end getMObFromStr():


ctrlMObArray = om2.MObjectArray()
ctrlPointArray = om2.MPointArray()
# iter sel and save ctrl MObs and world positions.
for thisDag in iterDagPathFromSelection():
	if thisDag.node().hasFn(om2.MFn.kTransform):
		worldMtx = om2.MTransformationMatrix(thisDag.inclusiveMatrix())
		worldVec = worldMtx.translation(om2.MSpace.kWorld)

		ctrlMObArray.append(thisDag.node())
		ctrlPointArray.append(worldVec)

nCtrls = len(ctrlMObArray)

if nCtrls < 2:
	raise ValueError('--A selection of at least 2 controllers is required.')

inCurvTransformFn, inNurbsFn = makeCurvFromPoints(ctrlPointArray)

dgMod = om2.MDGModifier()
dcmpMtxMObArray = om2.MObjectArray()

for i in xrange(nCtrls):
	thisDcmpMOb = dgMod.createNode("decomposeMatrix")
	dgMod.renameNode(thisDcmpMOb, "{0}_drive_cv{1}_dcmpM".format(name, i))
	dcmpMtxMObArray.append(thisDcmpMOb)

	thisCtrlFnDep = om2.MFnDependencyNode(ctrlMObArray[i])
	outMtxPlug = thisCtrlFnDep.findPlug("worldMatrix", 1)
	outMtxPlug = outMtxPlug.elementByLogicalIndex(0)

	thisDcmpFnDep = om2.MFnDependencyNode(thisDcmpMOb)
	inMtxPlug = thisDcmpFnDep.findPlug("inputMatrix", 1)
	outTranPlug = thisDcmpFnDep.findPlug("outputTranslate", 1)

	thisCvPointPlug = inNurbsFn.findPlug("controlPoints", 1)
	thisCvPointPlug = thisCvPointPlug.elementByLogicalIndex(i)

	dgMod.connect(outMtxPlug, inMtxPlug)
	dgMod.connect(outTranPlug, thisCvPointPlug)

# --------input curve shape-----------------------------------------------
inCurvWorldPlug = inNurbsFn.findPlug("worldSpace", 1)
inCurvWorldPlug = inCurvWorldPlug.elementByLogicalIndex(0)
dgMod.renameNode(inNurbsFn.object(), "%s_input_curvShape" % name)

folcCmds = cmds.createNode('follicle', n='%s_folc' % name)
folcMOb = getMObFromStr(folcCmds)
folcFnDep = om2.MFnDependencyNode(folcMOb)
folcStartPosPlug = folcFnDep.findPlug("startPosition", 1)
folcOutHairPlug = folcFnDep.findPlug("outHair", 1)
folcCurrPosPlug = folcFnDep.findPlug("currentPosition", 1)
folcOutCurvPlug = folcFnDep.findPlug("outCurve", 1)
dgMod.renameNode(folcMOb, "%s_folcShape" % name)

dgMod.connect(inCurvWorldPlug, folcStartPosPlug)

folcRestPlug = folcFnDep.findPlug("restPose", 1)
folcDirectionPlug = folcFnDep.findPlug("startDirection", 1)
if nCtrls > 3:
	folcDegreePlug = folcFnDep.findPlug('degree', 1)
	folcRestPlug.setInt(1)
	folcDirectionPlug.setInt(1)
	folcDegreePlug.setInt(3)

# --------hair system shape-----------------------------------------------
hairSysCmds = cmds.createNode('hairSystem', n='%s_hairSysShape' % name)
hairSysMOb = getMObFromStr(hairSysCmds)
hairSFnDep = om2.MFnDependencyNode(hairSysMOb)
hairSInHairPlug = hairSFnDep.findPlug('inputHair', 1)
hairSInHairPlug = hairSInHairPlug.elementByLogicalIndex(0)
hairSOutHairPlug = hairSFnDep.findPlug('outputHair', 1)
hairSOutHairPlug = hairSOutHairPlug.elementByLogicalIndex(0)
hairSCurrStatePlug = hairSFnDep.findPlug('currentState', 1)
hairSStartStatePlug = hairSFnDep.findPlug('startState', 1)
hairSNextPlug = hairSFnDep.findPlug('nextState', 1)
hairSFramePlug = hairSFnDep.findPlug('startFrame', 1)
hairSTimePlug = hairSFnDep.findPlug('currentTime', 1)

dgMod.connect(folcOutHairPlug, hairSInHairPlug)
dgMod.connect(hairSOutHairPlug, folcCurrPosPlug)

# --------nucleus---------------------------------------------------------
nucleusCmds = cmds.createNode('nucleus', n='%s_nucleus' % name)
nucleusMOb = getMObFromStr(nucleusCmds)
nucleusFnDep = om2.MFnDependencyNode(nucleusMOb)
nucleusSFramePlug = nucleusFnDep.findPlug('startFrame', 1)
nucleusOutObjPlug = nucleusFnDep.findPlug('outputObjects', 1)
nucleusTimePlug = nucleusFnDep.findPlug('currentTime', 1)
nucleusOutObjPlug = nucleusOutObjPlug.elementByLogicalIndex(0)
nucleusInActivePlug = nucleusFnDep.findPlug('inputActive', 1)
nucleusInActivePlug = nucleusInActivePlug.elementByLogicalIndex(0)
nucleusInAStartPlug = nucleusFnDep.findPlug('inputActiveStart', 1)
nucleusInAStartPlug = nucleusInAStartPlug.elementByLogicalIndex(0)

dgMod.connect(hairSCurrStatePlug, nucleusInActivePlug)
dgMod.connect(hairSStartStatePlug, nucleusInAStartPlug)
dgMod.connect(nucleusSFramePlug, hairSFramePlug)
dgMod.connect(nucleusOutObjPlug, hairSNextPlug)

# --------out curve-------------------------------------------------------
outCurvFn = makeCurvFromPoints(ctrlPointArray, inCurvTransformFn)[-1]
dgMod.renameNode(outCurvFn.object(), '%s_output_curvShape' % name)
outCurvCreatePlug = outCurvFn.findPlug('create', 1)

dgMod.connect(folcOutCurvPlug, outCurvCreatePlug)

# --------time------------------------------------------------------------
timeMOb = getMObFromStr('time1')
timeFnDep = om2.MFnDependencyNode(timeMOb)
timeOutPlug = timeFnDep.findPlug('outTime', 1)

dgMod.connect(timeOutPlug, nucleusTimePlug)
dgMod.connect(timeOutPlug, hairSTimePlug)

# --------point on curve info---------------------------------------------
dagMod = om2.MDagModifier()
dgMod.doIt()  # have to generate curve positions so getParamAtPoint evaluates correctly

locFnArray = []
pntOnCurveFnArray = []
dcmpFnArray = []
fourMtxFnArray = []
vecPFnArray = []
pointOnCurvePosPlugArray = om2.MPlugArray()

for ii in xrange(nCtrls):
	thisOutParam = outCurvFn.getParamAtPoint(ctrlPointArray[ii], 10)
	thisPocMOb = dgMod.createNode("pointOnCurveInfo")
	pntOnCurveFnArray.append(om2.MFnDependencyNode(thisPocMOb))
	thisPocInPlug = pntOnCurveFnArray[ii].findPlug("inputCurve", 1)
	pointOnCurvePosPlugArray.append(pntOnCurveFnArray[ii].findPlug("position", 1))

	dgMod.connect(folcOutCurvPlug, thisPocInPlug)

	thisPocParamPlug = pntOnCurveFnArray[ii].findPlug("parameter", 1)
	thisPocParamPlug.setFloat(thisOutParam)

	locMOb = dagMod.createNode('locator')
	locFnArray.append(om2.MFnDependencyNode(locMOb))
	locTranPlug = locFnArray[ii].findPlug('translate', 1)
	locRotPlug = locFnArray[ii].findPlug('rotate', 1)

	dgMod.connect(pointOnCurvePosPlugArray[ii], locTranPlug)

	fourMtxMOb = dgMod.createNode('fourByFourMatrix')
	fourMtxFnArray.append(om2.MFnDependencyNode(fourMtxMOb))
	fourMtxOutPlug = fourMtxFnArray[ii].findPlug('output', 1)
	fourMtxIn10Plug = fourMtxFnArray[ii].findPlug('in10', 1)
	fourMtxIn11Plug = fourMtxFnArray[ii].findPlug('in11', 1)
	fourMtxIn12Plug = fourMtxFnArray[ii].findPlug('in12', 1)

	vecPMOb = dgMod.createNode('vectorProduct')
	vecPFnArray.append(om2.MFnDependencyNode(vecPMOb))
	vecPInYPlug = vecPFnArray[ii].findPlug('input1Y', 1)
	vecPOperationPlug = vecPFnArray[ii].findPlug('operation', 1)
	vecPInYPlug.setInt(1)
	vecPOperationPlug.setInt(3)
	vecPOutXPlug = vecPFnArray[ii].findPlug('outputX', 1)
	vecPOutYPlug = vecPFnArray[ii].findPlug('outputY', 1)
	vecPOutZPlug = vecPFnArray[ii].findPlug('outputZ', 1)

	dgMod.connect(vecPOutXPlug, fourMtxIn10Plug)
	dgMod.connect(vecPOutYPlug, fourMtxIn11Plug)
	dgMod.connect(vecPOutZPlug, fourMtxIn12Plug)

	dcmpMOb = dgMod.createNode('decomposeMatrix')
	dcmpFnArray.append(om2.MFnDependencyNode(dcmpMOb))
	dcmpInMtxPlug = dcmpFnArray[ii].findPlug('inputMatrix', 1)
	dcmpOutRotPlug = dcmpFnArray[ii].findPlug('outputRotate', 1)

	dgMod.connect(fourMtxOutPlug, dcmpInMtxPlug)
	dgMod.connect(dcmpOutRotPlug, locRotPlug)

rootCtrlWMtx = om2.MFnDependencyNode(ctrlMObArray[0]).findPlug('worldMatrix', 1)
rootCtrlWMtx = rootCtrlWMtx.elementByLogicalIndex(0)
veP0MtxPlug = vecPFnArray[0].findPlug('matrix', 1)
dgMod.connect(rootCtrlWMtx, veP0MtxPlug)

pmaFnArray = []
for j in xrange(nCtrls - 1):
	thisPmaMOb = dgMod.createNode('plusMinusAverage')
	pmaFnArray.append(om2.MFnDependencyNode(thisPmaMOb))
	pmaIn0Plug = pmaFnArray[j].findPlug('input3D', 1)
	pmaIn0Plug = pmaIn0Plug.elementByLogicalIndex(0)
	dgMod.connect(pointOnCurvePosPlugArray[j+1], pmaIn0Plug)
	pmaIn1Plug = pmaIn0Plug.array()
	pmaIn1Plug = pmaIn1Plug.elementByLogicalIndex(1)

	dgMod.connect(pointOnCurvePosPlugArray[j], pmaIn1Plug)

	pmaOperationPlug = pmaFnArray[j].findPlug('operation',  1)
	pmaOperationPlug.setInt(2)

	locWMtxPlug = locFnArray[j].findPlug('worldMatrix', 1)
	locWMtxPlug = locWMtxPlug.elementByLogicalIndex(0)

	vecPMtxPlug = vecPFnArray[j+1].findPlug('matrix', 1)

	dgMod.connect(locWMtxPlug, vecPMtxPlug)

	fourMtxIn00Plug = fourMtxFnArray[j].findPlug('in00', 1)
	fourMtxIn01Plug = fourMtxFnArray[j].findPlug('in01', 1)
	fourMtxIn02Plug = fourMtxFnArray[j].findPlug('in02', 1)

	pmaOutXPlug = pmaFnArray[j].findPlug('output3Dx', 1)
	pmaOutYPlug = pmaFnArray[j].findPlug('output3Dy', 1)
	pmaOutZPlug = pmaFnArray[j].findPlug('output3Dz', 1)

	dgMod.connect(pmaOutXPlug, fourMtxIn00Plug)
	dgMod.connect(pmaOutYPlug, fourMtxIn01Plug)
	dgMod.connect(pmaOutZPlug, fourMtxIn02Plug)

endPntTangentXPlug = pntOnCurveFnArray[-1].findPlug('tangentX', 1)
endPntTangentYPlug = pntOnCurveFnArray[-1].findPlug('tangentY', 1)
endPntTangentZPlug = pntOnCurveFnArray[-1].findPlug('tangentZ', 1)

fourMtxEndIn00Plug = fourMtxFnArray[-1].findPlug('in00', 1)
fourMtxEndIn01Plug = fourMtxFnArray[-1].findPlug('in01', 1)
fourMtxEndIn02Plug = fourMtxFnArray[-1].findPlug('in02', 1)

dgMod.connect(endPntTangentXPlug, fourMtxEndIn00Plug)
dgMod.connect(endPntTangentYPlug, fourMtxEndIn01Plug)
dgMod.connect(endPntTangentZPlug, fourMtxEndIn02Plug)

# 1st:
#	dcmp, loc, 4x4, vecP, poc, pma, root ctrl
# {1-n-1}:
#	dcmp, loc, 4x4, vecP, poc, pma, n-1 loc
# n:
#	dcmp, loc, 4x4, vecP, poc, n-1 loc


dagMod.doIt()
dgMod.doIt()
