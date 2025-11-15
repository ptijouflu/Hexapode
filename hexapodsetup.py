import constants
import typing
import dynamixel_sdk 
import functions

class HexapodSetup:

    def __init__(self):
        self.__port_handler = dynamixel_sdk.PortHandler(constants.DEVICENAME)
        if not self.__port_handler.openPort():
            print("Failed to open the port")
            functions.getch()
            quit()
        print("Succeeded to open the port")

        self.__packet_handler = dynamixel_sdk.PacketHandler(constants.PROTOCOL_VERSION)
        self.__group_sync_write = dynamixel_sdk.GroupSyncWrite(self.__port_handler, self.__packet_handler,
                                                               constants.ADDR_GOAL_POSITION,
                                                               constants.LEN_GOAL_POSITION)
        self.__group_sync_read = dynamixel_sdk.GroupSyncRead(self.__port_handler, self.__packet_handler,
                                                             constants.ADDR_PRESENT_POSITION,
                                                             constants.LEN_PRESENT_POSITION)

        if not self.__port_handler.setBaudRate(constants.BAUDRATE):
            print("Failed to change the baudrate")
            functions.getch()
            quit()
        print("Succeeded to change the baudrate")

        for dxl_id in constants.LIFT_SERVOS + constants.ROTATE_SERVOS:
            dxl_comm_result, dxl_error = self.__packet_handler.write1ByteTxRx(self.__port_handler, dxl_id,
                                                                              constants.ADDR_TORQUE_ENABLE,
                                                                              constants.TORQUE_ENABLE)
            if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
                print(
                    f"Error enabling torque for Dynamixel#{dxl_id}: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")
            elif dxl_error != 0:
                print(f"Error enabling torque for Dynamixel#{dxl_id}: {self.__packet_handler.getRxPacketError(dxl_error)}")
            else:
                print(f"Dynamixel#{dxl_id} has been successfully connected")

        for dxl_id in constants.LIFT_SERVOS + constants.ROTATE_SERVOS:
            dxl_comm_result, dxl_error = self.__packet_handler.write4ByteTxRx(self.__port_handler, dxl_id,
                                                                              constants.ADDR_PROFILE_VELOCITY,
                                                                              constants.PROFILE_VELOCITY)
            if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
                print(
                    f"Error setting profile velocity for Dynamixel#{dxl_id}: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")
            elif dxl_error != 0:
                print(
                    f"Error setting profile velocity for Dynamixel#{dxl_id}: {self.__packet_handler.getRxPacketError(dxl_error)}")
            dxl_comm_result, dxl_error = self.__packet_handler.write4ByteTxRx(self.__port_handler, dxl_id,
                                                                              constants.ADDR_PROFILE_ACCELERATION,
                                                                              constants.PROFILE_ACCELERATION)
            if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
                print(
                    f"Error setting profile acceleration for Dynamixel#{dxl_id}: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")
            elif dxl_error != 0:
                print(
                    f"Error setting profile acceleration for Dynamixel#{dxl_id}: {self.__packet_handler.getRxPacketError(dxl_error)}")

        for dxl_id in constants.LIFT_SERVOS + constants.ROTATE_SERVOS:
            dxl_addparam_result = self.__group_sync_read.addParam(dxl_id)
            if not dxl_addparam_result:
                print(f"[ID:{dxl_id:03d}] groupSyncRead addparam failed")
                quit()

    def __del__(self):
        for dxl_id in constants.LIFT_SERVOS + constants.ROTATE_SERVOS:
            dxl_comm_result, dxl_error = self.__packet_handler.write1ByteTxRx(self.__port_handler, dxl_id,
                                                                              constants.ADDR_TORQUE_ENABLE,
                                                                              constants.TORQUE_DISABLE)
            if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
                print(
                    f"Error disabling torque for Dynamixel {dxl_id}: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")
            elif dxl_error != 0:
                print(
                    f"Error disabling torque for Dynamixel {dxl_id}: {self.__packet_handler.getRxPacketError(dxl_error)}")
        self.__port_handler.closePort()

    def write_position(self, coeff_positions):
        """Write the goal positions of each servo into the robot

        :type coeff_positions: typing.Dict[int, float]
        :return:
        """

        goal_positions = {}

        for dxl_id, position in coeff_positions.items():
            if dxl_id in constants.LIFT_SERVOS:
                goal_position = round(constants.lift_positions[0] + ((constants.lift_positions[1] - constants.lift_positions[0]) * position))
            elif dxl_id in constants.ROTATE_SERVOS:
                goal_position = round(constants.rotate_positions[dxl_id][0] + ((
                                                                                       constants.rotate_positions[dxl_id][1] - constants.rotate_positions[dxl_id][0]) * position))
            else:
                continue

            # transforme la position en tableau de bytes
            param_goal_position = [
                dynamixel_sdk.DXL_LOBYTE(dynamixel_sdk.DXL_LOWORD(goal_position)),
                dynamixel_sdk.DXL_HIBYTE(dynamixel_sdk.DXL_LOWORD(goal_position)),
                dynamixel_sdk.DXL_LOBYTE(dynamixel_sdk.DXL_HIWORD(goal_position)),
                dynamixel_sdk.DXL_HIBYTE(dynamixel_sdk.DXL_HIWORD(goal_position))
            ]

            # print(f'Dynamixel#{dxl_id} goal position: {goal_position}')

            dxl_addparam_result = self.__group_sync_write.addParam(dxl_id, param_goal_position)

            if not dxl_addparam_result:
                print(f"[ID:{dxl_id:03d}] groupSyncWrite addparam failed")
                quit()

            goal_positions[dxl_id] = goal_position

        # Envoi les positions au robot
        dxl_comm_result = self.__group_sync_write.txPacket()
        if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
            print(f"Error during SyncWrite: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")

        # Supprime les positions du buffer
        self.__group_sync_write.clearParam()

        # Le robot est en train de se deplacer (boucle tant que déplacement)
        while True:

            # Lecture de la position
            dxl_comm_result = self.__group_sync_read.txRxPacket()

            if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
                print(f"Error during SyncRead: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")

            all_reached = True

            for dxl_id in coeff_positions.keys():
                # Recuperation de la position d'un servo
                dxl_present_position = self.__group_sync_read.getData(dxl_id, constants.ADDR_PRESENT_POSITION,
                                                                      constants.LEN_PRESENT_POSITION)
                if dxl_present_position is None:
                    print(f"Error reading position for Dynamixel {dxl_id}")
                    all_reached = False
                    break

                # Check si sa position objective a ete atteinte
                # print(f'Dynamixel#{dxl_id} position: {abs(goal_positions[dxl_id] - dxl_present_position)} '
                #       f'(present : {dxl_present_position} obj : {goal_positions[dxl_id]})')
                if abs(goal_positions[dxl_id] - dxl_present_position) > constants.DXL_MOVING_STATUS_THRESHOLD:
                    all_reached = False
                    break

            if all_reached:
                break

    def read_pos(self):
        """ Print the position of each servo of the robot

        :rtype: None
        """

        # Lecture de la position
        dxl_comm_result = self.__group_sync_read.txRxPacket()

        if dxl_comm_result != dynamixel_sdk.COMM_SUCCESS:
            print(f"Error during SyncRead: {self.__packet_handler.getTxRxResult(dxl_comm_result)}")

        for dxl_id in range(1, 13):
            # Recuperation de la position d'un servo
            dxl_present_position = self.__group_sync_read.getData(dxl_id, constants.ADDR_PRESENT_POSITION,
                                                                  constants.LEN_PRESENT_POSITION)
            if dxl_present_position is None:
                print(f"Error reading position for Dynamixel {dxl_id}")
                break

    def set_torque_enable(self, dxl_id, enable):
        """
        Active ou désactive le torque d'un servo.
        :param dxl_id: ID du servo
        :param enable: 1 pour activer, 0 pour désactiver
        """
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port, dxl_id, 64, enable  # 64 = adresse du registre Torque Enable
        )
        if dxl_comm_result != 0:  # 0 = COMM_SUCCESS
            print(f"Erreur de communication avec le servo {dxl_id}")

    def close_port(self):
        """Ferme le port série."""
        self.port.closePort()