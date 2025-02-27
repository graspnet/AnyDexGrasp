import copy
import os
import json
import xlrd2
import numpy as np
import open3d as o3
from transforms3d.euler import euler2mat, quat2mat
import pybullet as p
import pybullet_data
import math
from tqdm import tqdm
import sys
import time
from angles2stl import AllegroAngles2STLs
from ur_toolbox.robot.Allegro.Allegro_grasp import grasp_types

joint_mesh_mapping = {"base": "base_link.STL",
                      "0": "link_0.0.STL",
                      "1": "link_1.0.STL",
                      "2": "link_2.0.STL",
                      "3": "link_3.0.STL",
                      "4": "link_3.0_tip.STL",
                      "5": "link_0.0.STL",
                      "6": "link_1.0.STL",
                      "7": "link_2.0.STL",
                      "8": "link_3.0.STL",
                      "9": "link_3.0_tip.STL",
                      "10": "link_0.0.STL",
                      "11": "link_1.0.STL",
                      "12": "link_2.0.STL",
                      "13": "link_3.0.STL",
                      "14": "link_3.0_tip.STL",
                      "15": "link_12.0_right.STL",
                      "16": "link_13.0.STL",
                      "17": "link_14.0.STL",
                      "18": "link_15.0.STL",
                      "19": "link_15.0_tip.STL",}


def four_meta_to_matrix(x):
    xyz = [x[0], x[1], x[2]]
    rpy = [x[6], x[3], x[4], x[5]]

    rot_mat = quat2mat(rpy)
    return np.array([[rot_mat[0][0], rot_mat[0][1], rot_mat[0][2], xyz[0]],
                     [rot_mat[1][0], rot_mat[1][1], rot_mat[1][2], xyz[1]],
                     [rot_mat[2][0], rot_mat[2][1], rot_mat[2][2], xyz[2]],
                     [0, 0, 0, 1]], dtype=np.float32)

def read_excel_2D_angle_to_12D_angle(path_16d, vis):
    angles = [[] for _ in range(len(grasp_types))]

    wb_6d = xlrd2.open_workbook(path_16d) 
    for pose_id in range(len(grasp_types)):
        sheet_6d = wb_6d.sheet_by_index(pose_id)

        widths = sheet_6d.col_values(0)[1:]
        widths = np.array(widths) * 0.1

        thumb0 = sheet_6d.col_values(1)[1:]
        thumb1 = sheet_6d.col_values(2)[1:]
        thumb2 = sheet_6d.col_values(3)[1:]
        thumb3 = sheet_6d.col_values(4)[1:]

        index0 = sheet_6d.col_values(5)[1:]
        index1 = sheet_6d.col_values(6)[1:]
        index2 = sheet_6d.col_values(7)[1:]
        index3 = sheet_6d.col_values(8)[1:]

        middle0 = sheet_6d.col_values(9)[1:]
        middle1 = sheet_6d.col_values(10)[1:]
        middle2 = sheet_6d.col_values(11)[1:]
        middle3 = sheet_6d.col_values(12)[1:]

        ring0 = sheet_6d.col_values(13)[1:]
        ring1 = sheet_6d.col_values(14)[1:]
        ring2 = sheet_6d.col_values(15)[1:]
        ring3 = sheet_6d.col_values(16)[1:]
        for ids, _ in enumerate(widths):
            if thumb0[ids] == -1:
                continue
            angles[pose_id].append([index0[ids], index1[ids], index2[ids], index3[ids], 0, middle0[ids], middle1[ids], middle2[ids], middle3[ids], 0,
                            ring0[ids], ring1[ids], ring2[ids], ring3[ids], 0,  thumb0[ids], thumb1[ids], thumb2[ids], thumb3[ids], 0,
                            widths[ids]])
    return angles

def open_pybullet(urdf_path):
    clid = p.connect(p.SHARED_MEMORY)
    if (clid < 0):
        p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setPhysicsEngineParameter(solverResidualThreshold=0, maxNumCmdPer1ms=1000)
    fps = 240
    timeStep = 1. / fps
    p.setTimeStep(timeStep)
    p.resetDebugVisualizerCamera(cameraDistance=1.3, cameraYaw=38, cameraPitch=-22,
                                 cameraTargetPosition=[0.35, -0.13, 0.5])

    flags = p.URDF_ENABLE_CACHED_GRAPHICS_SHAPES

    base_orn = [0, 0, 0]
    base_orn = p.getQuaternionFromEuler(base_orn)

    hand = p.loadURDF(urdf_path, [0.0, 0.0, 0.0], base_orn, useFixedBase=True)
    return p, hand

def get_mesh(po, id, PATH):
    t_angle = four_meta_to_matrix(po)
    
    path_file = PATH + joint_mesh_mapping[str(id)]
    link = o3.io.read_triangle_mesh(path_file)
    lingk_mesh = copy.deepcopy(link)

    link = link.transform(t_angle)
    link_mesh = lingk_mesh.transform(t_angle)    
    return link, link_mesh

def save_stl_and_pointcloud(name, angle, mesh, output_path):
    if not os.path.exists(output_path + 'source/' + name):
        os.makedirs(output_path + 'source/' + name)
    save_stl_path = output_path + 'source/' + name + '/' + str(np.round(angle[-1], 1)) + '.STL'
    o3.io.write_triangle_mesh(save_stl_path, mesh)

    pcd = o3.geometry.TriangleMesh.sample_points_uniformly(mesh, 300000)
    pcd.estimate_normals(search_param=o3.geometry.KDTreeSearchParamHybrid(radius=0.01, max_nn=30))
    points = np.array(pcd.points)
    pcd_extend = o3.geometry.PointCloud()
    pcd_extend.points = o3.utility.Vector3dVector(points)
    for i in range(1, 6):
        pcd_saved = pcd_extend.voxel_down_sample(0.001 * i)
        if not os.path.exists(output_path + 'source_pointclouds/voxel_size_' + str(i) + '/' + name):
            os.makedirs(output_path + 'source_pointclouds/voxel_size_' + str(i) + '/' + name)
        save_pcd_path = output_path + 'source_pointclouds/voxel_size_' + str(i) + '/' + name + '/' + str(np.round(angle[-1], 1)) + '.ply'
        o3.io.write_point_cloud(save_pcd_path, pcd_saved)

def get_meshes(angles, stl_path, output_path, width_16D_angle_json, urdf_path, vis):
    p, hand = open_pybullet(urdf_path)
    angles_to_stls = AllegroAngles2STLs(grasp_types)
    width_16D_angle = dict()
    for grasp_type, angle8 in enumerate(angles):
        print(grasp_type)
        for ids in tqdm([i for i in range(len(angle8))]):
            angle = angle8[ids]
            width = np.round(angle[-1], 1)

            path_file = stl_path + joint_mesh_mapping['base']
            base = o3.io.read_triangle_mesh(path_file)
            base_mesh = copy.deepcopy(base)
            frame = o3.geometry.TriangleMesh.create_coordinate_frame(0.1)
            pose = [[] for _ in range(20)]
            for joint_id in range(20):
                p.resetJointState(hand, joint_id, angle[joint_id])
            
            for joint_id in range(20):
                po = p.getLinkState(hand, joint_id)
                pose[joint_id] = [po[4][0], po[4][1], po[4][2], po[5][0], po[5][1],po[5][2],po[5][3]]
            
            for joint_id in range(20):
                mesh, link_mesh = get_mesh(pose[joint_id], joint_id, stl_path)
                base = base + mesh
                base_mesh = base_mesh + link_mesh
            
            origin = (angles_to_stls.get_center_orientation(base, [3103, 0]) + angles_to_stls.get_center_orientation(base, [3103, 1])) / 2
            origin_matrix = np.array([[1, 0, 0, origin[0]],
                                      [0, 1, 0, origin[1]],
                                      [0, 0, 1, origin[2]],
                                      [0, 0, 0, 1]])
            base.transform(np.linalg.inv(origin_matrix))
            base_mesh.transform(np.linalg.inv(origin_matrix))

            base.compute_triangle_normals()
            base_mesh.compute_triangle_normals()
            name = grasp_types[str(grasp_type+1)]['name']
            if not vis:
                save_stl_and_pointcloud(name, angle, base_mesh, output_path)
            
            translation, rotation = angles_to_stls.get_pose_information(base, grasp_type, width, vis=vis)
            translation, rotation = translation.tolist(), rotation.tolist()
            if str(name) not in width_16D_angle.keys():
                width_16D_angle[name] = dict()
            angle_16d = [angles[grasp_type][ids][:4]] + [angles[grasp_type][ids][5:9]] + [angles[grasp_type][ids][10:14]] + [angles[grasp_type][ids][15:19]]
            width_16D_angle[name][str(width)] = {'16d': angle_16d, 'translation': translation,  'rotation': rotation}

    if not vis:
        json_str = json.dumps(width_16D_angle, indent=4)
        with open(width_16D_angle_json, 'w') as json_file:
            json_file.write(json_str)
            
def generate_one_stl(urdf_path, stl_path, save_stl_path):
    p, hand = open_pybullet(urdf_path)
    num_mesh = len(joint_mesh_mapping)-1
    path_file = stl_path + joint_mesh_mapping['base']
    base = o3.io.read_triangle_mesh(path_file)
    base_mesh = copy.deepcopy(base)
    frame = o3.geometry.TriangleMesh.create_coordinate_frame(0.1)
    pose = [[] for _ in range(num_mesh)]
    for joint_id in range(num_mesh):
        ag = 0
        if joint_id == 15: 
            ag = 1.396
        p.resetJointState(hand, joint_id, ag)
    
    for joint_id in range(num_mesh):
        po = p.getLinkState(hand, joint_id)
        pose[joint_id] = [po[4][0], po[4][1], po[4][2], po[5][0], po[5][1],po[5][2],po[5][3]]
    
    for joint_id in range(num_mesh):
        mesh, link_mesh = get_mesh(pose[joint_id], joint_id, stl_path)
        base = base + mesh
        base_mesh = base_mesh + link_mesh
    base_mesh.compute_triangle_normals()
    o3.io.write_triangle_mesh(save_stl_path, base_mesh)
    print(base_mesh)

if __name__ == '__main__':
    path_16d = './generate_mesh_and_pointcloud/allegro_urdf/allegro_width_to_angle.xls'

    source_stl_path = './generate_mesh_and_pointcloud/allegro_urdf/allegro_hand_description/meshes/'
    output_path = './generate_mesh_and_pointcloud/allegro_urdf/meshes/'
    json_path = './generate_mesh_and_pointcloud/allegro_urdf/width_16D_angle.json'

    urdf_path = './generate_mesh_and_pointcloud/allegro_urdf/allegro_hand_description/urdf/allegro_hand_description_right.urdf'
    vis = False
    angles = read_excel_2D_angle_to_12D_angle(path_16d, vis=vis)
    get_meshes(angles, source_stl_path, output_path, json_path, urdf_path, vis=vis)




