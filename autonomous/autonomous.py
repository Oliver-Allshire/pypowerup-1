"""The autonomous controls for the robot."""
import math
import wpilib
from magicbot.state_machine import AutonomousStateMachine, state
from components.vision import Vision
from components.lifter import Lifter
from automations.lifter import LifterAutomation
from automations.motion import ChassisMotion
from automations.intake import IntakeAutomation
from pyswervedrive.swervechassis import SwerveChassis
from utilities.bno055 import BNO055
from robot import Robot


class OverallBase(AutonomousStateMachine):
    """statemachine designed to intelegently respond to possible situations in auto"""

    vision: Vision
    lifter: Lifter
    lifter_automation: LifterAutomation
    bno055: BNO055
    chassis: SwerveChassis
    ds: wpilib.DriverStation

    # automations
    motion: ChassisMotion
    intake_automation: IntakeAutomation
    lifter_automation: LifterAutomation

    cube_switch: wpilib.DigitalInput  # the switch used to confirm cube capture during early testing

    def on_enable(self):
        self.lifter.reset.pos()
        self.game_data_message = self.ds.getGameSpecificMessage()
        self.picking_up_cube = True  # is the robot trying to pickup a cube or deposit?
        # make y +ve or -ve depending on where we start
        self.navigation_point = [5.6, 2.4, 0, 1]
        self.switch_enabled = True
        self.double_scale_strategy = True  # this will be set by the dashboard
        self.start_side = 'R'  # set by the dashboard
        self.scale_objective = True
        self.opposite = True  # does the robot need to swap sides?
        if len(self.game_data_message) == 3:
            self.fms_scale = self.game_data_message[1]  # L or R
            self.fms_switch = self.game_data_message[0]  # L or R
        else:
            # need defaults
            self.fms_scale = 'R'
            self.fms_switch = 'R'
        self.chassis.odometry_x = Robot.length / 2
        self.chassis.odometry_y = 0
        super().on_enable()

    @state(first=True)
    def setup(self):
        """Do robot initilisation specific to the statemachine in here."""
        if self.start_side == self.fms_switch:
            self.scale_objective = False
            self.next_state("go_to_switch")
            #change switch postion one off
        else:
            if self.double_scale_strategy:
                self.scale_objective = True
            if self.start_side == self.fms_switch:
                self.opposite = True
            else:
                self.opposite = False
            self.next_state("navigating")

    def invert_co_ordinates(self, co_ordinate):
        """Inverts the y-coordinates of the input annd returns the output"""
        for i in co_ordinate:
            co_ordinate[i][1] *= -1
        return co_ordinate


'''     def close_to_objective(self, objective):
        """checks if the robot is on the same side of the field as the objective."""
        if self.start_side == self.fms_switch and objective == 'switch':
            return True
        else:
            return False
        if self.start_side == self.fms_scale and objective == 'scale':
            return True
        else:
            return False

    def target_objective(self):
        """A dictionary function that gives an output on the order of objectives based on inputs.
        inputs are designated on the left in a tuple in the order of robot start side, strategy,
        switch side scale side. Outputs are given on the right in the order which the
        robot needs to go to"""
        objective_calculation = {
            # Double scale with right start
            ('R', 'double_scale', 'L', 'L'): ('cross_l_scale', 'same_l_scale'),
            ('R', 'double_scale', 'R', 'L'): ('cross_l_scale', 'same_l_scale'),
            ('R', 'double_scale', 'R', 'R'): ('same_r_scale', 'same_r_scale'),
            ('R', 'double_scale', 'L', 'R'): ('same_r_scale', 'same_r_scale'),
            # Double scale with left start
            ('L', 'double_scale', 'L', 'L'): ('same_l_scale', 'same_l_scale'),
            ('L', 'double_scale', 'R', 'L'): ('same_l_scale', 'same_l_scale'),
            ('L', 'double_scale', 'R', 'R'): ('cross_r_scale', 'same_r_scale'),
            ('L', 'double_scale', 'L', 'R'): ('cross_r_scale', 'same_r_scale'),
            # Switch and scale with right start
            ('R', 'switch_and_scale', 'L', 'R'): ('cross_l_scale', 'same_r_scale'),
            ('R', 'switch_and_scale', 'L', 'L'): ('cross_l_scale', 'same_l_switch'),
            ('R', 'switch_and_scale', 'R', 'L'): ('same_r_switch', 'cross_l_scale'),
            ('R', 'switch_and_scale', 'R', 'R'): ('same_r_switch', 'same_r_scale'),
            # Switch and scale with left start
            ('L', 'switch_and_scale', 'R', 'L'): ('same_l_scale', 'cross_r_switch'),
            ('L', 'switch_and_scale', 'R', 'R'): ('cross_r_scale', 'same_r_switch'),
            ('L', 'switch_and_scale', 'L', 'R'): ('same_l_switch', 'cross_r_scale'),
            ('L', 'switch_and_scale', 'L', 'L'): ('same_l_switch', 'same_l_scale')
        }
        return objective_calculation[(self.start_side, self.strategy, self.fms_switch,
                                      self.fms_scale)] '''

    @state
    def navigating(self, initial_call):
        """The robot navigates to one of two nav-points, if the one it is at is the wrong one,
        it swaps to the opposite side."""
        if initial_call:
            angle = self.bno055.getAngle()
            #seraching for objective
            if not self.picking_up_cube:
                if self.opposite:
                    # go to other navigation point
                    self.navpoint = self.invert_co_ordinates(self.navpoint)
                    # invert the y-co-ordinates of the navpoint
                    self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y, angle, 0],
                                               self.navigation_point])
                else:
                    # at correct nav point
                    self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y, angle, 0],
                                               self.navigation_point])

                if self.scale_objective:
                    self.next_state('go_to_scale')
                else:
                    self.next_state('go_to_switch')
            else:
                #serach for cube , nav  point close to us
                self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y, angle, 0],
                                           self.navigation_point])
                self.next_state("go_to_cube")
            #self.picking_up_cube=not(picking_up_cube)

    @state
    def go_to_cube(self, initial_call):
        """The robot drives towards where the next cube should be"""
        if initial_call:
            angle = self.bno055.getAngle()
            self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y,
                                       angle, 0]])
        if not self.motion.enabled:
            self.next_state("lifting")

    @state
    def lifting(self, initial_call):
        """The robot lifts then releases its cube into either the scale or switch.
        Makes use of the external lifting statemachine"""
        if initial_call:
            self.picking_up_cube = True
            # toggles the navpoint to cube pickup mode
            if self.chassis.odometry_y < 0:
                self.navpoint[2] = 5 * math.pi / 4
            else:  # changes the facing of the navpoint based on which side the
                # robot is on TODO test this!
                self.navpoint[2] = 3 * math.pi / 4
        self.lifter_automation.engage()
        # Release cube
        if self.lifter_automation.is_executing():
            self.next_state("navigating")

    @state
    def turn_and_go_to_cube(self, initial_call):
        """The robot rotates in the direction specified by the vision
        system while moving towards the cube. Combines two angles to find the absolute
        angle towards the cube"""
        if initial_call:
            angle = self.bno055.getAngle()
            vision_angle = self.vision.largest_cube()
            # print(vision_angle)
        if vision_angle is None:
            self.next_state("search_for_cube")
            print("========searching for cube========")
            return
        absolute_cube_direction = angle + vision_angle
        new_heading = angle + 0.2 * vision_angle
        self.chassis.field_oriented = True
        self.chassis.set_velocity_heading(math.cos(absolute_cube_direction),
                                          math.sin(absolute_cube_direction),
                                          new_heading)

    @state
    def search_for_cube(self):
        """The robot confirms that there is a cube within the frame of the camera.
        if it detects  one it moves towards it, if it does not it rotates to try to find a cube"""
        if self.vision.largest_cube() is None:
            self.chassis.set_inputs(0, 0, 1)
        else:
            self.next_state("turn_and_go_to_cube")

    @state
    def go_to_switch(self, initial_call):
        """The robot travels to the switch"""
        if initial_call:
            self.switch_enabled = False
            self.scale_objective = True
            if self.start_side == self.fms_scale:
                self.opposite = False
            else:
                self.opposite = True
        if self.fms_switch == 'L':
            # go to left switch
            pass
        if self.fms_switch == 'R':
            # go to right switch
            pass
        self.next_state("lifting")

    @state
    def go_to_scale(self, initial_call):
        """The robot travels to the scale"""
        if initial_call:
            # change switch position
            if self.switch_enabled:
                self.scale_objective = False
                if self.start_side == self.fms_scale:
                    self.opposite = 1
            else:
                self.opposite = 0
        if self.fms_scale == 'L':
            # go to left scale
            pass
        if self.fms_scale == 'R':
            # go to right scale
            pass
        self.next_state("lifting")


class VisionTest(OverallBase):
    """To test the vision system"""
    DEFAULT = True
    MODE_NAME = 'Vision Test'

    @state
    def go_to_cube(self, initial_call):
        """The robot drives towards where the next cube should be"""
        if initial_call:
            angle = self.bno055.getAngle()
            self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y, angle, 0],
                                       [2.5, 0, math.pi/2, 1.5],
                                       [2.5, 1, math.pi/2, 1.5]])
        if not self.motion.enabled:
            print("going to 'intake cube'")
            # self.next_state("search_for_cube")
            self.next_state_now("lifting")

    @state
    def intake_cube(self):
        """Attempts to intake the cube, judges success off of the external
        intake statemachine and the cube microswitch. if the colection is
        successful, toggles the wapoint to objective mode"""
        self.intake_automation.engage()
        if not self.intake_automation.is_executing() and not self.cube_switch.get():
            # intake stops running
            # TODO add current spike measurement
            self.picking_up_cube = False
            # sets the navpoint to objective mode
            self.next_state("go_to_scale")
        elif not self.intake_automation.is_executing() and self.cube_switch.get():
            # After completing the intake cycle there is no cube
            self.next_state("search_for_cube")

    @state(first=True)
    def go_to_scale(self, initial_call):
        """The robot travels to the scale"""
        if initial_call:
            angle = self.bno055.getAngle()
            self.motion.set_waypoints([[self.chassis.odometry_x, self.chassis.odometry_y, angle, 0],
                                       [6, 0, 0, 0]])
        if not self.motion.enabled:
            print("================= At scale ======================")
            self.next_state("go_to_cube")
