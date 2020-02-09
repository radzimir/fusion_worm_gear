import adsk.core, adsk.fusion, traceback, math

'''
# Worm Gear Geneartor

This is a scipt for modeling work gears in Fusion 360 environment.
As fas as i know, there is until now no other method/tool to make CYCLOIDAL worm gear in fusion.
It models worm wheel by sequantially rotating and cut-combining bodies.
It is intended to be uses with FDM printing and should hopefully deliver sufficient precision for printing.
Please adjust values in Model class to get desired worm gear.

# NOTES FOR FUSION DESIGNERS - HowTo

## Initial setup for design allowing replacement of worm wheel

To start using a generated wheel and worm:

1. Generate worm gear and save.
2. Open new design, and make 'insert into current design'
3. break link to allow copying of bodies
4. make new component for your worm wheel
5. copy-paste generated body into new component
6. make any modifications you need, but do not use any refernce point or line from copied body to make replacement easily possible

## Replacement

If you wish to replace original wheel:

1. scroll timeline back to begining
2. remove imported wheel
3. import ne wone
4. copy paste body again
5. continue replaying timeline

# TODOs

1. try second approach with globoid worm, which is suprisingly easeire, see www.otvinta.com/tutorial02.html
   pro: easier wheel, defined fully parametrical without cutting operation.
   contra: warm must be printed with support

2. worm with more than one teeth/thread

3. add drive joint

# Notes for Developers

1. the construct if(True):... is uses to help fold a code in text editor.
2. global viables are:
    m    for Model
    c    for reusable Components
    ui   for User interface

# REFERNCES

* http://www.tandwiel.info/de/verzahnungen/nomenklatur-verzahnungen-tandwiel-info/
* http://www.tandwiel.info/de/verzahnungen/zahnstangemit-gerad-verzahnung-verzahnungen-tandwiel-info/
* http://www.tmoells.de/downloads/Zahnradberechnung.pdf
    
'''

# make some context objects global
ui = None # Fusion UI
m  = None # model of the gear
c  = None # components

class Model:
    def __init__(self):

        ###################################################
        # START OF PARAMETERS SECTION YOU MAY/SHOUD ADJUST

        # Terminology by http://www.tandwiel.info/de/verzahnungen/nomenklatur-verzahnungen-tandwiel-info/
        
        # Multiply module by 0.1 to convert from mm into internal cm unit
        self.module=0.1*1
        self.pressureAngle=fromGrad(20)
        self.wheelTeethNumber=20.0 # must be even number
        self.wormRotations=5

        '''
        2  - for initial testing
        10 - OK
        15 - OK
        17 - probably some cut errors, result quality OK
        20 - probably somecut errors,  result quality perfect even for undercut if pressent
        '''
        self.cuttingStepsProWormTurn=2 # min 2

        # switch on for development
        self.timelineCapture = False

        # due to mysterious gaps increase revolve angle of initial body by 1%
        self.oversizeToAvoidGapsInCircularrPattern = 1.01

        # END OF PARAMETERS SECTION YOU MAY/SHOUD ADJUST
        ###################################################


        # 
        # calculated gear parameters
        #
        self.pich=self.module*math.pi
        self.addendum=1.16*self.module
        self.dedendum=1.25*self.module
        self.fillet=0.1*self.module
        self.clearanceBottom=0.1*self.module
        self.clearanceTop=0.2*self.module

        self.wormReferenceDiameter = 12*self.module
        self.wormReferenceRadius = self.wormReferenceDiameter/2
        self.wormLength = self.pich*self.wormRotations
        self.wormLeadAngle=math.atan(self.pich/(math.pi*self.wormReferenceDiameter))

        self.wheelAngularPich=2.0*math.pi/self.wheelTeethNumber
        self.wheelDiameter=self.module*self.wheelTeethNumber
        self.wheelStrenght=self.wormReferenceRadius*2

        #
        # documentation text
        #
        self.textLocationPoint3D = adsk.core.Point3D.create(0, -self.wheelDiameter, 0)
        self.textSize=2*self.module
        self.textStyle = adsk.fusion.TextStyles.TextStyleBold
        self.textFontName = 'Courier New'
        self.textLineSpacing = 6 * self.textSize

class Components:
    def __init__(self,app):
        self.app=app
        self.ui = self.app.userInterface

        # for new design any time
        self.design = self.app.activeProduct

        # Get the root component of the active design.
        self.rootComp = self.design.rootComponent
        self.features = self.rootComp.features
        self.sketches = self.rootComp.sketches
        self.revolves = self.features.revolveFeatures
        self.sweeps   = self.features.sweepFeatures
        self.planes   = self.rootComp.constructionPlanes
        self.occurrences = self.rootComp.occurrences
        self.planeXZ = self.rootComp.xZConstructionPlane
        self.planeXY = self.rootComp.xYConstructionPlane
        self.documentationSketch = None

def run(context):
    global c
    global ui
    global m
    try:

        # start new design any time, do not record history
        adsk.core.Application.get().documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)

        c = Components(adsk.core.Application.get())
        ui = c.ui 
        m = Model()

        if( not m.timelineCapture ):
            c.design.designType = adsk.fusion.DesignTypes.DirectDesignType

        # sketch worm gear main sketch - worm core and wheel 
        if(True):
            c.documentationSketch = c.sketches.add(c.planeXY)
            c.documentationSketch.name = 'Documentation'

            mainSketch = c.sketches.add(c.planeXY)
            mainSketch.name = "Main"

            # lines definiing core
            lines = mainSketch.sketchCurves.sketchLines
            cs = CoordinateSystem(0,-m.wormLength/2,0)
            wormAxisLine =                  lines.addByTwoPoints( cs.point(0, 0, 0), cs.point(0, m.wormLength, 0) )
            wormProfileSketchPlaneLine =    lines.addByTwoPoints( wormAxisLine.startSketchPoint, cs.point(m.wormReferenceRadius, 0, 0) )
            wormCoreCylinderLine =          lines.addByTwoPoints( wormProfileSketchPlaneLine.endSketchPoint , cs.point(m.wormReferenceRadius, m.wormLength, 0) )
            wormCoreCylinderLine.isConstruction=True
            wormCoreEndEdge =               lines.addByTwoPoints( wormAxisLine.endSketchPoint, wormCoreCylinderLine.endSketchPoint )
        
            # construction line for placing wheel cross section sketch
            wheelCrossSectionPlaneConstructionLine = lines.addByTwoPoints( point(m.wormReferenceRadius, 0, m.module), point(m.wormReferenceRadius, 0, -m.module) )
            wheelCrossSectionPlaneConstructionLine.isConstruction = True

            # construction line for rotating wheel
            wheelAxisLine = lines.addByTwoPoints( point( m.wormReferenceRadius+m.wheelDiameter/2, 0, m.module), point( m.wormReferenceRadius+m.wheelDiameter/2, 0, -m.module) )
            wheelAxisLine.isConstruction = True

            # pich circle
            circles = mainSketch.sketchCurves.sketchCircles
            pichCircle = circles.addByCenterRadius( point( m.wormReferenceRadius+m.wheelDiameter/2, 0, 0), m.wheelDiameter/2 )
            pichCircle.isConstruction = True

        # wheel profile
        if(True):
            # create a wheel component under root component
            occ1 = c.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            wheelComponent = occ1.component
            wheelComponent.name="Wheel"

            sketchWheelProfile = wheelComponent.sketches.add(c.planeXZ)
            sketchWheelProfile.name = "WheelProfile"
            lines = sketchWheelProfile.sketchCurves.sketchLines
            cs = CoordinateSystem(m.wormReferenceRadius, 0, 0)
            lineUp         = lines.addByTwoPoints( cs.point(-m.dedendum*2,-m.wheelStrenght/2,0), cs.point(m.addendum*2,-m.wheelStrenght/2,0) )
            lineInternalEdge = lines.addByTwoPoints( lineUp.endSketchPoint , cs.point(m.addendum*2, m.wheelStrenght/2,0) )
            lineDown         = lines.addByTwoPoints( lineInternalEdge.endSketchPoint , cs.point(-m.dedendum*2, m.wheelStrenght/2,0) )
            lineInternalEdge = lines.addByTwoPoints( lineDown.endSketchPoint , lineUp.startSketchPoint )
            wheelProfile = sketchWheelProfile.profiles.item(0)

            revolveFeatureInput = wheelComponent.features.revolveFeatures.createInput(wheelProfile, wheelAxisLine, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            
            
            revolveFeatureInput.setAngleExtent(True, byReal( m.oversizeToAvoidGapsInCircularrPattern * m.wheelAngularPich ) )

            wheelExtrusion = wheelComponent.features.revolveFeatures.add(revolveFeatureInput)

        # milling worm tooth profile
        if(True):
            occ1 = c.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            wormMillComponent = occ1.component
            wormMillComponent.name="WormMill"

            # Get construction planes
            planeInput = c.planes.createInput()

            # Add construction plane angled from 
            leadAngleValueInput = byReal( m.wormLeadAngle )
            planeInput.setByAngle(wormProfileSketchPlaneLine, leadAngleValueInput, c.planeXY)
            wormProfilePlane = c.planes.add(planeInput)
            makeWorm(wormMillComponent, wormProfilePlane, wormAxisLine, True)

        # documentation
        if(True):
            printlnOnMainSketch( 'axis distance  = '+str(10*(m.wormReferenceRadius+m.wheelDiameter/2))+'mm' )
            printlnOnMainSketch( 'teeth on wheel = '+str(m.wheelTeethNumber) )

        if(True):
            #
            # Mill wheel 
            #

            wormTurns=6 # should be even number

            # initial rotation of a wheel to starting position
            rotateWheel(wheelComponent, wheelAxisLine, - wormTurns/2 * m.wheelAngularPich)
            
            steps = wormTurns*m.cuttingStepsProWormTurn
            whealRotationAngle = wormTurns * m.wheelAngularPich / steps
            wormRotationAngle = wormTurns * 2*math.pi / steps

            for i in range(1, steps+1 ):
                #
                # cut
                #
                wormBody = wormMillComponent.bRepBodies.item(0)
                wheelBody  = wheelComponent.bRepBodies.item(0)
        
                toolBodies = adsk.core.ObjectCollection.create()
                toolBodies.add(wormBody)
                
                combineFeatures = c.features.combineFeatures
                combineFeatureInput = combineFeatures.createInput(wheelBody, toolBodies )
                combineFeatureInput.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                combineFeatureInput.isKeepToolBodies = True

                try:
                    combineFeatures.add(combineFeatureInput)
                except:
                    print( 'Cut produces exception, just ignoring this time...\n' )

                rotateWheel(wheelComponent, wheelAxisLine, whealRotationAngle)

                #
                # rotate worm mill
                #

                # Create a collection of entities for move
                entitiesForRotation = adsk.core.ObjectCollection.create()
                entitiesForRotation.add(wormBody)

                # Create a transform to do move
                transform = adsk.core.Matrix3D.create()
                transform.setToRotation( -wormRotationAngle, wormAxisLine.worldGeometry.asInfiniteLine().direction, wormAxisLine.worldGeometry.startPoint)

                # Create a move feature
                moveFeatures = wormMillComponent.features.moveFeatures
                moveFeatureInput = moveFeatures.createInput(entitiesForRotation, transform)
                moveFeatures.add(moveFeatureInput)

            # rotate wheel body and join toogether
            wheelBody  = wheelComponent.bRepBodies.item(0)
            entitiesForPattern = adsk.core.ObjectCollection.create()
            entitiesForPattern.add( wheelBody )
            circularPatternFeatures = wheelComponent.features.circularPatternFeatures
            circularPatternFeaturesInput = circularPatternFeatures.createInput(entitiesForPattern,  wheelAxisLine )
            circularPatternFeaturesInput.quantity = adsk.core.ValueInput.createByReal( m.wheelTeethNumber/2 )
            circularPatternFeaturesInput.isSymmetric = False
            circularPatternFeaturesInput.totalAngle = byReal(2*math.pi)
            circularFeature = circularPatternFeatures.add(circularPatternFeaturesInput)

            # combine teeth into whole wheel
            toolBodies = adsk.core.ObjectCollection.create()
            for i in range(1, wheelComponent.bRepBodies.count):
                toolBodies.add( wheelComponent.bRepBodies.item(i) )
            
            combineFeatures = wheelComponent.features.combineFeatures
            combineFeatureInput = combineFeatures.createInput( wheelBody, toolBodies )
            combineFeatureInput.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            combineFeatureInput.isKeepToolBodies = False
            combineFeatures.add(combineFeatureInput)

            wheelBody.name = "Wheel_"+str(m.wheelTeethNumber)

        # make final work-worm
        if(True):
            occ1 = c.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            wormComponent = occ1.component
            wormComponent.name="Worm"
            makeWorm(wormComponent, wormProfilePlane, wormAxisLine, False)

        #
        # finishing work
        #

        # activate root component
        c.design.activateRootComponent()

        # deactivate milling worm
        c.rootComp.allOccurrencesByComponent(wormMillComponent).item(0).isLightBulbOn = False
        # show documentation sketch
        c.documentationSketch.isLightBulbOn = True

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def point(x,y,z):
    return adsk.core.Point3D.create(x, y, z)

def fromGrad(grad):
    '''
    Convert grad angle to radians
    '''
    #return byReal(mm/10)
    return (grad/180) * math.pi

def byReal(value):
    return adsk.core.ValueInput.createByReal(value)

class CoordinateSystem:

    def __init__( self ):
        self.offsetX=0
        self.offsetY=0
        self.offsetZ=0

    def __init__( self, x, y, z ):
        self.offsetX=x
        self.offsetY=y
        self.offsetZ=z

    def point( self, x, y, z ):
        return point(x+self.offsetX, y+self.offsetY, z+self.offsetZ)

    def drawAxies( self, lines ):
            x = lines.addByTwoPoints(self.point(0, 0, 0), self.point(10, 0, 0))
            x.isConstruction=True
            y = lines.addByTwoPoints(self.point(0, 0, 0), self.point(0, 5, 0))
            y.isConstruction=True

def metricProfile(sketch, csMain, milling):
    '''
    milling=True for milling/cutting profile
    milling=False for final profile of the worm used for print
    Returns wormCoreRadiusCalibrated - radius needed to match profile with a core cylinder
    '''
    global c
    global ui
    global m

    lines = sketch.sketchCurves.sketchLines

    # move cs to 1/4 of pich line
    csSideLine = CoordinateSystem(csMain.offsetX, csMain.offsetY+m.pich/4, csMain.offsetZ)
    csSideLine.drawAxies(lines)

    # draw angled line, substract clearance if milling
    dedendunm = m.dedendum - (m.clearanceBottom if milling else 0)
    addedndum = m.addendum + (m.clearanceTop if milling else 0)

    bottomLine = lines.addByTwoPoints(
        csMain.point(-dedendunm,m.pich/2,0),
        csSideLine.point( -dedendunm , dedendunm*math.tan(m.pressureAngle), 0 )
    )

    sideLineBottomMiddle = lines.addByTwoPoints( 
        bottomLine.endSketchPoint,
        csSideLine.point( 0, 0, 0 )
    )

    sideLineMiddleTop = lines.addByTwoPoints(
        sideLineBottomMiddle.endSketchPoint,
        csSideLine.point( +addedndum , -addedndum*math.tan(m.pressureAngle), 0 ), 
    )

    topLine = lines.addByTwoPoints(
        sideLineMiddleTop.endSketchPoint,
        csMain.point(addedndum,0,0)
    )

    bottomFillet = sketch.sketchCurves.sketchArcs.addFillet(
        bottomLine, bottomLine.endSketchPoint.geometry, 
        sideLineBottomMiddle, sideLineBottomMiddle.startSketchPoint.geometry, 
        m.fillet
    )

    topFillet = sketch.sketchCurves.sketchArcs.addFillet(
        sideLineMiddleTop, sideLineMiddleTop.endSketchPoint.geometry, 
        topLine, topLine.startSketchPoint.geometry,
        m.fillet
    )

    bottomProfileClosing = lines.addByTwoPoints(
        bottomLine.endSketchPoint,
        csMain.point( -dedendunm, 0, 0)
    )
    # unused for now
    symetryLine = lines.addByTwoPoints(
        csMain.point( -dedendunm, 0, 0),
        csMain.point( addedndum, 0, 0)
    )
    symetryLine.isConstruction=True

    # mirror profile, mirroring not supported by API, do it manually
    bottomLineMirrored = mirrorLineY(sketch, bottomLine)

    sideLineBottomMiddleMirrored = mirrorLineY(sketch, sideLineBottomMiddle)

    sketch.sketchCurves.sketchArcs.addFillet(
        bottomLineMirrored, bottomLineMirrored.endSketchPoint.geometry, 
        sideLineBottomMiddleMirrored, sideLineBottomMiddleMirrored.startSketchPoint.geometry,
        m.fillet
    )

    sideLineMiddleTopMirrored = mirrorLineY(sketch, sideLineMiddleTop)
    topLineMirrored = mirrorLineY(sketch, topLine)

    sketch.sketchCurves.sketchArcs.addFillet(
        sideLineMiddleTopMirrored, sideLineMiddleTopMirrored.endSketchPoint.geometry,
        topLineMirrored, topLineMirrored.startSketchPoint.geometry, 
        m.fillet
    )

    bottomProfileClosingMirrored = mirrorLineY(sketch, bottomProfileClosing)

    # calculate radius of the core
    pointOnYAxis = bottomFillet.worldGeometry.startPoint.copy()
    pointOnYAxis.x=0
    pointOnYAxis.z=0
    return bottomFillet.worldGeometry.startPoint.distanceTo(pointOnYAxis)

def makeWorm(wormComponentParam, wormProfilePlane, wormAxisLine, milling):
    wormProfileSketch = wormComponentParam.sketches.add(wormProfilePlane)
    wormProfileSketch.name="WormProfile"

    # make coordinate system in the midle of origin, move Y by worm radius
    csMain = CoordinateSystem( m.wormReferenceRadius/2, 0, 0 )
    # csMain.drawAxies(lines)
    
    wormCoreRadiusCalibrated = metricProfile(wormProfileSketch, csMain, milling)

    # milling worm core
    sketchWormCore = c.sketches.add(c.planeXZ)
    sketchWormCore.name = "WormCore"
    sketchWormCore.sketchCurves.sketchCircles.addByCenterRadius( point(0,0,0), wormCoreRadiusCalibrated )
    
    extrudeFeatureInput = wormComponentParam.features.extrudeFeatures.createInput( sketchWormCore.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrudeFeatureInput.setSymmetricExtent(byReal(m.wormLength+m.pich), True)
    wormComponentParam.features.extrudeFeatures.add(extrudeFeatureInput)

    # Create a sweep input
    wormAxisPath = c.rootComp.features.createPath(wormAxisLine, False) # no chaining
    
    sweepInput = wormComponentParam.features.sweepFeatures.createInput( wormProfileSketch.profiles.item(0) ,wormAxisPath, adsk.fusion.FeatureOperations.JoinFeatureOperation )
    sweepInput.twistAngle = byReal( 2*math.pi*m.wormRotations )
    sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    
    # Create the sweep.
    sweep = wormComponentParam.features.sweepFeatures.add(sweepInput)


#TODO: write perfect mirrr function based on https://www.geeksforgeeks.org/find-mirror-image-point-2-d-plane/ , or wait until Fusin implements mirroring
def mirrorLineY(sketch,sketchLine):
    return sketch.sketchCurves.sketchLines.addByTwoPoints(
        point( sketchLine.geometry.startPoint.x, -sketchLine.geometry.startPoint.y, 0 ),
        point( sketchLine.geometry.endPoint.x,   -sketchLine.geometry.endPoint.y,   0)
    )

def mirrorFilletY(sketch,fillet):
    return sketch.sketchCurves.sketchArcs.add (
        point( sketchLine.geometry.startPoint.x, -sketchLine.geometry.startPoint.y, 0 ),
        point( sketchLine.geometry.endPoint.x,   -sketchLine.geometry.endPoint.y,   0)
    )

def rotateWheel(wheelComponent, wheelAxisLine, gearRotationAngle):
    wheelBody  = wheelComponent.bRepBodies.item(0)

    # Create a collection of entities for move
    entitiesForRotation = adsk.core.ObjectCollection.create()
    entitiesForRotation.add(wheelBody)

    # Create a transform to do move
    transform = adsk.core.Matrix3D.create()
    transform.setToRotation( gearRotationAngle, wheelAxisLine.worldGeometry.asInfiniteLine().direction, wheelAxisLine.worldGeometry.startPoint)

    # Create a move feature
    moveFeatures = wheelComponent.features.moveFeatures
    moveFeatureInput = moveFeatures.createInput(entitiesForRotation, transform)
    moveFeatures.add(moveFeatureInput)

def printlnOnMainSketch(text):
    sketchTexts = c.documentationSketch.sketchTexts
    sketchTextInput = sketchTexts.createInput(text, m.textSize, m.textLocationPoint3D)
    sketchTextInput.textStyle = m.textStyle
    sketchTextInput.fontName = m.textFontName
    sketchText = sketchTexts.add(sketchTextInput)
    m.textLocationPoint3D.y = m.textLocationPoint3D.y - m.textSize*m.textLineSpacing
