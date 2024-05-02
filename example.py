import apriltag
import cv2
import numpy as np
import sys
import pyrealsense2 as rs

W = 640
H = 480

#Define camera focal length and the real width of apriltag
focal_length = 1930/3
tag_width = 35 #assume the real width of apriltag is 0.05 m

# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, W, H, rs.format.z16, 30)
config.enable_stream(rs.stream.color, W, H, rs.format.bgr8, 30)

print("[INFO] start streaming...")
pipeline.start(config)

def perspective_projection(focal_length,tag_width, pixel_width):
    distance = (tag_width * focal_length) / pixel_width
    return distance

while True:
    frames = pipeline.wait_for_frames()
    
    color_frame = frames.get_color_frame()
    color_data = np.asanyarray(color_frame.get_data())
    
    gray = cv2.cvtColor(color_data, cv2.COLOR_BGR2GRAY)

    at_detector = apriltag.Detector(apriltag.DetectorOptions(families='tag36h11'))

    tags = at_detector.detect(gray)
    #print(tags)
    #print("%d apriltags have been detected."%len(tags))
    """
    for tag in tags:
        cv2.circle(color_data, tuple(tag.corners[0].astype(int)),4,(255,0,0),2)
        cv2.circle(color_data, tuple(tag.corners[1].astype(int)),4,(255,0,0),2)
        cv2.circle(color_data, tuple(tag.corners[2].astype(int)),4,(255,0,0),2)
        cv2.circle(color_data, tuple(tag.corners[3].astype(int)),4,(255,0,0),2)
    """
    for tag in tags:
        # 绘制检测到的 AprilTag 的角点
        for corner in tag.corners:
            cv2.circle(color_data, tuple(corner.astype(int)), 4, (255, 0, 0), 2)
        
         # 计算并打印 AprilTag 的像素宽度
        width_in_pixels = np.linalg.norm(tag.corners[0] - tag.corners[1])
        width_in_pixels = width_in_pixels
        print("AprilTag ID:", tag.tag_id, "Width in pixels:", width_in_pixels)

        # Use width_in_pixels outside the loop
        distance = perspective_projection(focal_length, tag_width, width_in_pixels)
        #print("Distance to AprilTag ID:", tag.tag_id, "is:", distance)

        # Pose estimation
        obj_points = np.array([[-tag_width/2, tag_width/2, 0], [tag_width/2, tag_width/2, 0],
                               [tag_width/2, -tag_width/2, 0], [-tag_width/2, -tag_width/2, 0]])
        img_points = np.array(tag.corners, dtype=np.float32)
        camera_matrix = np.array([[focal_length, 0, W/2], [0, focal_length, H/2], [0, 0, 1]])
        dist_coeffs = np.zeros((4,1))  # Assuming no lens distortion
        
        ret, rotation_vector, translation_vector = cv2.solvePnP(obj_points, img_points, camera_matrix, dist_coeffs)
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        #print("Rotation Matrix:", rotation_matrix)
        print("Translation Vector:", translation_vector)
    
    

    cv2.imshow("apriltag_test",color_data)
    
    if cv2.waitKey(1) == ord('q'):
        break

pipeline.stop