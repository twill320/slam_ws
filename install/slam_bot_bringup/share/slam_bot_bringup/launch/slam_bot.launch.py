# Copyright 2022 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.actions import IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node


def generate_launch_description():
    # === CONFIGURE ARGUMENTS AND PATHS ===
    # MODIFIED: Changed package names to match your workspace structure
    pkg_project_bringup = get_package_share_directory('slam_bot_bringup')
    pkg_project_description = get_package_share_directory('slam_bot_description')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Launch argument to control RViz
    use_rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Open RViz.'
    )

    # === LOAD THE ROBOT MODEL ===
    # We load the SDF file as a string to pass to the robot_state_publisher and the spawner
    # MODIFIED: Corrected the path to the SDF file to include the 'slam_bot' directory
    sdf_file  =  os.path.join(pkg_project_description, 'models', 'slam_bot', 'model.sdf')
    with open(sdf_file, 'r') as infp:
        robot_desc = infp.read()

    # === CONFIGURE NODES ===

    # 1. LAUNCH GAZEBO SIMULATION
    # We launch an empty world. The robot will be spawned in later.
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r -v 4 empty.sdf'}.items() # -r: run simulation on start
    )

    # 2. SPAWN THE ROBOT
    # The 'ros_gz_sim.create' node is a convenient way to spawn models in Gazebo
    # It will call the /create service with the model details
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', robot_desc,
            '-name', 'slam_bot', # MODIFIED: Changed robot name
            '-allow_renaming', 'true'
        ],
        output='screen'
    )

    # 3. ROBOT STATE PUBLISHER
    # Takes the robot description and joint states and publishes TF transforms for all links
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[
            {'use_sim_time': True},
            {'robot_description': robot_desc},
        ]
    )

    # 4. GAZEBO <-> ROS BRIDGE
    # This node translates messages between Gazebo and ROS 2
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='parameter_bridge',
        arguments=[
            '--ros-args', '-p',
            # MODIFIED: Changed config file name to match your project
            f"config_file:={os.path.join(pkg_project_bringup, 'config', 'slam_bot_bridge.yaml')}"
        ],
        output='screen'
    )

    # 5. RVIZ VISUALIZER
    # Launches RViz2 with the pre-configured layout
    rviz = Node(
       package='rviz2',
       executable='rviz2',
       # MODIFIED: Changed rviz file name to match your project
       arguments=['-d', os.path.join(pkg_project_bringup, 'config', 'slam_bot.rviz')],
       condition=IfCondition(LaunchConfiguration('rviz'))
    )

    # === ASSEMBLE THE LAUNCH DESCRIPTION ===
    return LaunchDescription([
        use_rviz_arg,
        gz_sim,
        bridge,
        spawn_robot,
        robot_state_publisher,
        rviz
    ])
