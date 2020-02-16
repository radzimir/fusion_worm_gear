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

1. try second approach with globoid worm, which is suprisingly easier, see www.otvinta.com/tutorial02.html
   pro: easier wheel, defined fully parametrical without cutting operation.
   contra: warm must be printed with support

2. worm with more than one teeth/thread

3. add drive joint

4. experiment with UI update while computing geometry

5. add mode with cutting all around ( without circle pattern ), add timing measurement and compare both trategies

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
        self.module = 0.1*1
        self.pressureAngle = fromGrad(20)
        self.wheelTeethNumber = 60 # must be even number
        self.wormRotations = 5
        self.wormAxisAngle = fromGrad(15)

        '''
        2  - for initial testing
        10 - OK
        15 - OK
        17 - probably some cut errors, result quality OK
        20 - probably somecut errors,  result quality perfect, long calculating time, many small faces
        '''
        self.cuttingStepsProWormTurn = 20 # minimal 2

        # switch on for development
        self.timelineCapture = True

        #
        # tweeking parameters
        #

        # due to mysterious gaps increase revolve angle of initial body by 1%, test if really needed in particular case
        #self.oversizeToAvoidGapsInCircularrPattern = 1.01
        self.oversizeToAvoidGapsInCircularrPattern = 1

        # top profile of cutting worm may rounded with small filets 
        # or replaced by big arc - usefoul to make an underuct for small
        # wheels very smooth
        self.cuttingTopProfileAsArc=True

        # END OF PARAMETERS SECTION YOU MAY/SHOUD ADJUST
        ###################################################

        if(True):
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
            self.textLocationPoint3D = adsk.core.Point3D.create(0, -max( self.wheelDiameter, self.wormLength ) , 0 )
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

        c.documentationSketch = c.sketches.add(c.planeXY)
        c.documentationSketch.name = 'Documentation'

        # main sketch
        if(True):
            # sketch worm gear main sketch - worm core and wheel 
            wheelMainSketch = c.rootComp.sketches.add(c.planeXY)
            wheelMainSketch.name = "Main"

            # pich circle
            circles = wheelMainSketch.sketchCurves.sketchCircles
            pichCircle = circles.addByCenterRadius( point( m.wormReferenceRadius+m.wheelDiameter/2, 0, 0), m.wheelDiameter/2 )
            pichCircle.isConstruction = True

            # construction line for placing wheel cross section sketch
            lines = wheelMainSketch.sketchCurves.sketchLines
            # cs = CoordinateSystem(0,0,0)
            # cs.drawAxies(lines)
            wheelCrossSectionPlaneConstructionLine = lines.addByTwoPoints( point(m.wormReferenceRadius, 0, m.module), point(m.wormReferenceRadius, 0, -m.module) )
            wheelCrossSectionPlaneConstructionLine.isConstruction = True

            # construction line for rotating wheel
            wheelAxisLine = lines.addByTwoPoints( point( m.wormReferenceRadius+m.wheelDiameter/2, 0, m.module), point( m.wormReferenceRadius+m.wheelDiameter/2, 0, -m.module) )
            wheelAxisLine.isConstruction = True

            # construction line for  placing angled worm plane
            wormPlaneConstructionLine = lines.addByTwoPoints( point(m.wormReferenceRadius, 0,0), point(-m.wormReferenceRadius, 0,0) )
            wormPlaneConstructionLine.isConstruction = True

        wheelComponent = makeWheelFragment(wheelAxisLine)

        # main worm sketch
        if(True):
            # construction plane for placing worm sketch
            constructionPlaneInput = c.rootComp.constructionPlanes.createInput()
            constructionPlaneInput.setByAngle( wormPlaneConstructionLine, byReal(  -m.wormAxisAngle ), c.rootComp.xYConstructionPlane )
            wormConstructionPlane = c.rootComp.constructionPlanes.add( constructionPlaneInput )

            mainSketch = c.rootComp.sketches.add( wormConstructionPlane )
            mainSketch.name = "WormPlacement"

            lines = mainSketch.sketchCurves.sketchLines

            cs = CoordinateSystem( 0, 0, 0 )
            cs.directionX=-1
            cs.directionY=-1    
            cs.drawAxies(lines)
            wormAxisLine =                  lines.addByTwoPoints( cs.point(0, -m.wormLength/2, 0), cs.point(0, m.wormLength/2, 0) )
            # wormAxisLine.isConstruction = True
            wormProfileSketchPlaneLine =    lines.addByTwoPoints( cs.point(-m.wormReferenceRadius, -m.wormLength/2, 0), cs.point(m.wormReferenceRadius, -m.wormLength/2, 0) )
            wormProfileSketchPlaneLine.isConstruction = True
            # wormCoreCylinderLine =          lines.addByTwoPoints( wormProfileSketchPlaneLine.endSketchPoint , cs.point(m.wormReferenceRadius, m.wormLength/2, 0) )
            # wormCoreCylinderLine.isConstruction=True
            # wormCoreEndEdge =               lines.addByTwoPoints( wormAxisLine.endSketchPoint, wormCoreCylinderLine.endSketchPoint )
            # wormCoreEndEdge.isConstruction = True

        # make cutting worm
        wormCuttingComponent = makeWorm(wormConstructionPlane, wormProfileSketchPlaneLine, wormPlaneConstructionLine, wormAxisLine, True)

        sketchDocumentation()

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
                wormBody = wormCuttingComponent.bRepBodies.item(0)
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
                    print( 'Cut produces exception, just ignoring, it will hopefully work anyway...' )

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
                moveFeatures = wormCuttingComponent.features.moveFeatures
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

            # combine wheel fragments into whole wheel
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
        wormComponent = makeWorm(wormConstructionPlane, wormProfileSketchPlaneLine, wormPlaneConstructionLine, wormAxisLine, False)

        #
        # finishing work
        #

        # activate root component
        c.design.activateRootComponent()

        # deactivate cutting worm
        c.rootComp.allOccurrencesByComponent(wormCuttingComponent).item(0).isLightBulbOn = False
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
        self.directionX=1
        self.directionY=1
        self.directionZ=1

    def __init__( self, x, y, z ):
        self.offsetX=x
        self.offsetY=y
        self.offsetZ=z
        self.directionX=1
        self.directionY=1
        self.directionZ=1

    def point( self, x, y, z ):
        return point( 
            self.directionX * (x+self.offsetX), 
            self.directionY * (y+self.offsetY) , 
            self.directionZ * (z+self.offsetZ)
        )

    def drawAxies( self, lines ):
            x = lines.addByTwoPoints(self.point(0, 0, 0), self.point(10, 0, 0))
            x.isConstruction=True
            y = lines.addByTwoPoints(self.point(0, 0, 0), self.point(0, 5, 0))
            y.isConstruction=True

    def mirrorPointY(self, pointY):
        return -(pointY - self.directionY * self.offsetY)

    #TODO: write perfect mirrr function based on https://www.geeksforgeeks.org/find-mirror-image-point-2-d-plane/ , or wait until Fusin implements mirroring
    def mirrorLineY(self, sketch, sketchLine):
        return sketch.sketchCurves.sketchLines.addByTwoPoints(
            self.point( sketchLine.geometry.startPoint.x - self.directionX*self.offsetX , self.mirrorPointY(sketchLine.geometry.startPoint.y), 0 ),
            self.point( sketchLine.geometry.endPoint.x   - self.directionX*self.offsetX , self.mirrorPointY(sketchLine.geometry.endPoint.y),   0)
        )


def makeWheelFragment(wheelAxisLine):
    # create a wheel component under root component
    occ1 = c.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    wheelComponent = occ1.component
    wheelComponent.name="Wheel"

    # wheel profile
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

    return wheelComponent

def makeWorm(wormConstructionPlane, wormProfileSketchPlaneLine, wormPlaneConstructionLine, wormAxisLine, cutting):
    occ1 = c.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    wormComponent = occ1.component
    if( cutting ):
        wormComponent.name="WormCutting"
    else:
        wormComponent.name="Worm"

    #
    # tooth profile
    #

    # Get construction planes
    planeInput = wormComponent.constructionPlanes.createInput()

    # Add construction plane angled from 
    planeInput.setByAngle(wormProfileSketchPlaneLine, byReal( m.wormLeadAngle ), wormConstructionPlane)
    wormProfilePlane = wormComponent.constructionPlanes.add(planeInput)

    wormProfileSketch = wormComponent.sketches.add(wormProfilePlane)
    wormProfileSketch.name="Profile"

    cs = CoordinateSystem( m.wormReferenceRadius, 0, 0 )
    
    wormCoreRadiusCalibrated = metricProfile(wormProfileSketch, cs, cutting)

    #
    # worm core
    #

    # construction plane for placing worm core sketch
    constructionPlaneInput = wormComponent.constructionPlanes.createInput()
    constructionPlaneInput.setByAngle( wormPlaneConstructionLine, byReal( -(m.wormAxisAngle+math.pi/2) ), c.rootComp.xYConstructionPlane )
    wormCoreConstructionPlane = wormComponent.constructionPlanes.add( constructionPlaneInput )

    sketchWormCore = wormComponent.sketches.add(wormCoreConstructionPlane)
    sketchWormCore.name = "Core"
    sketchWormCore.sketchCurves.sketchCircles.addByCenterRadius( point(0,0,0), wormCoreRadiusCalibrated )
    
    extrudeFeatureInput = wormComponent.features.extrudeFeatures.createInput( sketchWormCore.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrudeFeatureInput.setSymmetricExtent(byReal(m.wormLength+m.pich), True)
    wormComponent.features.extrudeFeatures.add(extrudeFeatureInput)

    # Create a sweep input
    wormAxisPath = wormComponent.features.createPath(wormAxisLine, False) # no chaining
    
    sweepInput = wormComponent.features.sweepFeatures.createInput( wormProfileSketch.profiles.item(0) ,wormAxisPath, adsk.fusion.FeatureOperations.JoinFeatureOperation )
    sweepInput.twistAngle = byReal( 2*math.pi*m.wormRotations )
    sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    
    # Create the sweep.
    sweep = wormComponent.features.sweepFeatures.add(sweepInput)

    return wormComponent

def metricProfile(sketch, cs, cutting):
    '''
    milling=True for milling/cutting profile
    milling=False for final profile of the worm used for print
    Returns wormCoreRadiusCalibrated - radius needed to match profile with a core cylinder
    '''
    global c
    global ui
    global m

    lines = sketch.sketchCurves.sketchLines
    cs.drawAxies(lines)

    # move cs to 1/4 of pich line
    csSideLine = CoordinateSystem(cs.offsetX, cs.offsetY+m.pich/4, cs.offsetZ)

    # draw angled line, substract clearance if milling
    dedendunm = m.dedendum - (m.clearanceBottom if cutting else 0)
    addedndum = m.addendum + (m.clearanceTop if cutting else 0)

    bottomLine = lines.addByTwoPoints(
        cs.point(-dedendunm,m.pich/2,0),
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

    bottomFillet = sketch.sketchCurves.sketchArcs.addFillet(
        bottomLine, bottomLine.endSketchPoint.geometry, 
        sideLineBottomMiddle, sideLineBottomMiddle.startSketchPoint.geometry, 
        m.fillet
    )

    if( not cutting or not m.cuttingTopProfileAsArc ):
        topLine = lines.addByTwoPoints(
            sideLineMiddleTop.endSketchPoint,
            cs.point(addedndum,0,0)
        )

        topFillet = sketch.sketchCurves.sketchArcs.addFillet(
            sideLineMiddleTop, sideLineMiddleTop.endSketchPoint.geometry, 
            topLine, topLine.startSketchPoint.geometry,
            m.fillet
        )

    bottomProfileClosing = lines.addByTwoPoints(
        bottomLine.endSketchPoint,
        cs.point( -dedendunm, 0, 0)
    )

    # unused for now
    symetryLine = lines.addByTwoPoints(
        cs.point( -dedendunm, 0, 0),
        cs.point( addedndum, 0, 0)
    )
    symetryLine.isConstruction=True

    # mirror profile, mirroring not supported by API, do it manually
    bottomLineMirrored = cs.mirrorLineY(sketch, bottomLine)
    sideLineBottomMiddleMirrored = cs.mirrorLineY(sketch, sideLineBottomMiddle)

    sketch.sketchCurves.sketchArcs.addFillet(
        bottomLineMirrored, bottomLineMirrored.endSketchPoint.geometry, 
        sideLineBottomMiddleMirrored, sideLineBottomMiddleMirrored.startSketchPoint.geometry,
        m.fillet
    )

    sideLineMiddleTopMirrored = cs.mirrorLineY(sketch, sideLineMiddleTop)

    bottomProfileClosingMirrored = cs.mirrorLineY(sketch, bottomProfileClosing)

    if( cutting and m.cuttingTopProfileAsArc ):
        # make radius rounding top of the tooth
        # round top make an smooth undercut for wheels with small
        # number of teeth
        sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
            adsk.core.Point3D.create( sideLineMiddleTop.endSketchPoint.geometry.x - math.tan(m.pressureAngle) * sideLineMiddleTop.endSketchPoint.geometry.y , 0, 0) , 
            sideLineMiddleTop.endSketchPoint.geometry,
            -(math.pi-2*m.pressureAngle)
        )
    else:
        topLineMirrored = cs.mirrorLineY(sketch, topLine)

        sketch.sketchCurves.sketchArcs.addFillet(
            sideLineMiddleTopMirrored, sideLineMiddleTopMirrored.endSketchPoint.geometry,
            topLineMirrored, topLineMirrored.startSketchPoint.geometry, 
            m.fillet
        )

    # calculate radius of the core
    pointOnYAxis = bottomFillet.worldGeometry.startPoint.copy()
    pointOnYAxis.x=0
    pointOnYAxis.z=0
    return bottomFillet.worldGeometry.startPoint.distanceTo(pointOnYAxis)

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

def sketchDocumentation():
    # printlnOnMainSketch( 'axis distance  = '+str(10*(m.wormReferenceRadius+m.wheelDiameter/2))+'mm' )
    # printlnOnMainSketch( 'teeth on wheel = '+str(m.wheelTeethNumber) )
    # printlnOnMainSketch( 'cutting steps pro worm turn = '+str(m.cuttingStepsProWormTurn) )
    # printlnOnMainSketch( 'worm sxis angle = '+str(m.wormLength) )
    printlnOnMainSketch( 
        'DESIGN DATA:\n'
        '   wheel pich diameter = ' + str(10*m.wheelDiameter) + 'mm\n'
        '   axis distance  = '+str(10*(m.wormReferenceRadius+m.wheelDiameter/2))+'mm\n' +
        '   worm sxis angle = '+str( round(m.wormAxisAngle * 180/math.pi, 2) ) + '°\n' +
        '   worm length = '+str(10*m.wormLength)+'mm\n'
        '\n' +
        'META DATA:\n'+
        '   teeth on wheel = '+str(m.wheelTeethNumber) + '\n'
        '   cutting steps pro worm turn = '+str(m.cuttingStepsProWormTurn) + '\n'
    )

