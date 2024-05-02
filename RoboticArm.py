from AprilTag.scripts import apriltag
import cv2
import numpy as np
import pyrealsense2 as rs
from argparse import ArgumentParser
from frankx import *
import traceback
import time

import math
import json
import LLM

import ctypes
ctypes.CDLL('/home/medialab/yuming_test/robotic arm/AprilTag/lib/libapriltag.so', mode=ctypes.RTLD_GLOBAL)

class MotionPlaner():
    def __init__(self):
        self.parser = ArgumentParser()
        self.parser.add_argument('--host', default='172.16.0.2', help='FCI IP of the robot')
        self.args = self.parser.parse_args()
        self.robot_state = None
        self.record_pose = []
        self.record_grasp_obj_pose = None

        ## For record motion setting
        self.is_recording = False

        ## Set Robot arm parameter ##
        self.robot = Robot(self.args.host)
        self.robot.set_default_behavior()
        self.robot.recover_from_errors()
        self.robot.set_dynamic_rel(0.2)
        
        ## Set Gripper parameter ##
        self.gripper = self.robot.get_gripper()
        self.gripper.gripper_speed = 0.05
        self.gripper.gripper_force = 60
        self.GRIPPER_MAX_WIDTH = 0.08 # m

        ## Set the work mode
        self.stack_mode = False
        self.catch_mode = False
        self.is_grasp = False

        ## Offset array([x,y,z])
        self.catch_Offset = np.array([0.03 , 0.03 ,0.075])
        self.put_Offset = np.array([0.03 , 0.03 ,0.1])
    
    def openGripper(self):
        self.gripper.move(self.GRIPPER_MAX_WIDTH)
        self.is_grasp = False
        
    def closeGripper(self):
        self.is_grasp = self.gripper.clamp()
        if self.is_grasp:
            return True
        self.openGripper()
        return False

    def moveToHome(self):
        self.robot.move(JointMotion([0, -0.796, 0, -2.329, 0, 1.53, 0.785]))
        print("Go to Home")
    
    def moveToWorkSpace(self):
        self.robot.move(JointMotion([-0.78, -0.796, 0, -2.329, 0, 1.53, 0.785]))
        print("Go to Work Space")

    def getRobotState(self):
        self.robot_state = self.robot.read_once()
        print('\nPose: ', self.robot.current_pose())
        print('O_TT_E: ', self.robot_state.O_T_EE)
        print('Joints: ', self.robot_state.q)
        print('Elbow: ', self.robot_state.elbow)
        return self.robot_state

    def makeSureClamp(self):
        return self.is_grasp
    
    def thePositionOfApriltag(self):
        W = 640
        H = 480

        # Define camera focal length and the real width of apriltag
        focal_length = 1930/3
        tag_width = 35 #assume the real width of apriltag is 0.05 m

        # Configure depth and color streams
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, W, H, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, W, H, rs.format.bgr8, 30)

        print("[INFO] start streaming...")
        profile = pipeline.start(config)
        device = profile.get_device()
        device.hardware_reset()

        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        color_data = np.asanyarray(color_frame.get_data())
        gray = cv2.cvtColor(color_data, cv2.COLOR_BGR2GRAY)

        at_detector = apriltag.Detector(apriltag.DetectorOptions(families='tag36h11'))
        tags = at_detector.detect(gray)

        detected_id = []

        if self.stack_mode:
            for tag in tags:
                if tag.tag_id == 0:
                    detected_id.append(tag.tag_id)
            #print(detected_id)

        if self.catch_mode:
            for tag in tags:
                if tag.tag_id != 0:
                    detected_id.append(tag.tag_id)
            #print(detected_id)
        
        tvec = None  # Initialize tvec to None
        roll = None   # Initialize roll to None

        for tag in tags:
            target = detected_id[0]
            if tag.tag_id == target:
                obj_points = np.array([[-tag_width/2, tag_width/2, 0], [tag_width/2, tag_width/2, 0],
                                    [tag_width/2, -tag_width/2, 0], [-tag_width/2, -tag_width/2, 0]])
                img_points = np.array(tag.corners, dtype=np.float32)
                camera_matrix = np.array([[focal_length, 0, W/2], [0, focal_length, H/2], [0, 0, 1]])
                dist_coeffs = np.zeros((4,1))  
                
                ret, rvec, tvec = cv2.solvePnP(obj_points, img_points, camera_matrix, dist_coeffs)
                
                rotation_matrix, _ = cv2.Rodrigues(rvec)
                # Use the Rodrigues function to obtain Euler angles.
                eulerAngles = cv2.RQDecomp3x3(rotation_matrix)[0]
                yaw = round(eulerAngles[1],-1) 
                pitch = round(eulerAngles[0],-1)
                roll = round(eulerAngles[2],-1)

                if roll >=0:
                    roll = roll % 90
                    if roll < 50:
                        roll = roll
                    else:
                        roll = (90 - roll) *(-1)
                else:
                    roll = roll *(-1)
                    roll = roll % 90
                    if roll < 50:
                        roll = roll *(-1)
                    else:
                        roll = 90 - roll

                roll = math.radians(roll)

        pipeline.stop()
        
        return tvec, roll
    
    def coorTransform(self):
        translation, roll= self.thePositionOfApriltag()

        catch_vector = translation.copy()
        # Swap element 0 and 1
        catch_vector[0] = translation[1]
        catch_vector[1] = translation[0]

        #Transformation parameter
        T = np.array([[-1/1000,-1/1000,-1/1000]])
        
        if self.catch_mode == True:
            Offset = self.catch_Offset
        else:
            Offset = self.put_Offset

        #Apply transformation
        catch_vector = np.transpose(catch_vector)*T + Offset
        TR_vector = np.squeeze(catch_vector)

        return TR_vector, roll

    def moveForward(self, x=0, y=0, z=0, roll=0):
        way = Affine(x, y, z)
        motion_forward = LinearRelativeMotion(way)
        self.robot.move(motion_forward)
        
        state = self.robot.read_once()
        
        current_x = state.q[-1]  # the last joint is the one being adjusted
        adjusted_x = current_x + roll
        
        # Create a new list of joint positions with the adjusted x-coordinate
        new_joint_positions = list(state.q[:-1])  # Copy all joint positions except the last one
        new_joint_positions.append(adjusted_x)  # Add the adjusted x-coordinate
        
        joint_motion = JointMotion(new_joint_positions)
        self.robot.move(joint_motion)

    def catchOb(self):
        self.catch_mode = True

        translation, roll = self.coorTransform()
        self.moveForward(x=translation[0],y=translation[1],roll=roll)
    
        translation, roll = self.coorTransform()
        self.moveForward(x=translation[0],y=translation[1],roll=roll)

        translation, roll = self.coorTransform()
        self.moveForward( z=translation[2] ,roll = roll)

        self.closeGripper()

        self.robot.move(JointMotion([0, -0.796, 0, -2.329, 0, 1.53, 0.785]))
        print("Return to Initial pose complete")

        self.catch_mode = False
        return True
    
    def stackOb(self):
        self.stack_mode = True
        self.moveToWorkSpace()

        translation, roll = self.coorTransform()
        letMesee = 0.13
        # Translation Vector
        self.moveForward(x=translation[0]-letMesee,y=translation[1],roll=roll)

        translation, roll = self.coorTransform()
        # Translation Vector
        self.moveForward(x=translation[0],y=translation[1],z=translation[2],roll=roll)

        self.openGripper()

        self.moveForward(z=0.2)

        self.robot.move(JointMotion([0, -0.796, 0, -2.329, 0, 1.53, 0.785]))
        print("Return to Initial pose complete")
        
        self.stack_mode = False
        return True
    
    def giveMeOb(self):
        self.robot.move(JointMotion([-0.233, -0.245, -0.05, -1.94, 0.003, 1.736, 0.73]))
        start_time = time.time()  # Start time
        while True:
            motion_down = LinearRelativeMotion(Affine(0.0, 0.0, 0.0))
            motion_down_data = MotionData().with_reaction(Reaction(Measure.ForceZ > 5.0))
            self.robot.move(motion_down, motion_down_data)
            
            # Check if motion stopped due to force exceeding 5.0
            if motion_down_data.did_break:
                self.openGripper()
                time.sleep(3)
                self.robot.move(JointMotion([0, -0.796, 0, -2.329, 0, 1.53, 0.785]))
                break
    
            if time.time() - start_time > 10:
                self.robot.move(JointMotion([0, -0.796, 0, -2.329, 0, 1.53, 0.785]))
                break

            time.sleep(0.1)

    def lookfor(self):
        self.moveToHome()

        W = 640
        H = 480

        # Configure depth and color streams
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, W, H, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, W, H, rs.format.bgr8, 30)

        print("[INFO] start streaming...")
        profile = pipeline.start(config)
        device = profile.get_device()
        device.hardware_reset()

        at_detector = apriltag.Detector(apriltag.DetectorOptions(families='tag36h11'))

        def detect_tags():
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            color_data = np.asanyarray(color_frame.get_data())
            gray = cv2.cvtColor(color_data, cv2.COLOR_BGR2GRAY)
            
            tags = at_detector.detect(gray)
            for tag in tags:
                if tag.tag_id !=0:
                    return tags
                else:
                    tags = []
                    return tags
            
        def stop_motion():
            motion_down = LinearRelativeMotion(Affine(0.0, 0.0, 0.0))
            motion_down_data = MotionData().with_reaction(Reaction(Measure.ForceZ < 5.0))
            self.robot.move(motion_down, motion_down_data)
            self.robot.recover_from_errors()
            pipeline.stop()
            print("Find the object.")

        while True:
            tags = detect_tags()
            if tags:
                stop_motion()
                break

            self.robot.move(JointMotion([0.6, -0.796, 0, -2.329, 0, 1.53, 0.785]))
            tags = detect_tags()
            if tags:
                stop_motion()
                break
                
            self.robot.move(JointMotion([-0.3, -0.796, 0, -2.329, 0, 1.53, 0.785]))
            tags = detect_tags()
            if tags:
                stop_motion()
                break

            if not tags:
                pipeline.stop()
                self.moveToHome()
                break

    def putToBack(self):
        self.robot.move(JointMotion([0, 0.331, 0, -2.645, 0, 2.969, 0.785]))
        self.openGripper()
        self.moveToHome()
        print("Put back")     


def main():
    controller = MotionPlaner()
    
    command_dict = {
        ##basic function
        "home": controller.moveToHome,
        "work": controller.moveToWorkSpace,
        "check": controller.getRobotState,
        
        ##gripper state
        "open": controller.openGripper,
        "close": controller.closeGripper,
        "isgrasp": controller.makeSureClamp,

        #advance function
        "catch":controller.catchOb,
        "stack": controller.stackOb,
        "give": controller.giveMeOb,
        "lookfor":controller.lookfor,
        "putback":controller.putToBack,
        
    }
    while True:
        grasp_state = controller.makeSureClamp()
        #LLM.askuserneed(grasp_state)
        try:
            with open("selected_task.json", "r") as f:
                tasks = json.load(f)
            for cmd in tasks:
                cmd = input("cmd:")
                if cmd in command_dict:
                    command_dict[cmd]()
                elif cmd == "exit":
                    break
        except Exception as e:
            traceback.print_exc()
            break

if __name__ == '__main__':
    main()



