# **Controlling a robot arm using large language models**

## Project Goals

- Integrating Large Language Models (LLMs) with robotic arms, allowing users to directly manipulate the robotic arm through text.。

## Prerequisite

- **Franka Control Interface Documentation**
    - Overview
    - Minimum system and network requirements
    - Compatible versions
    - Installation on Linux or Installation on Windows
    - Getting started
    - libfranka
    - Robot and interface specifications
    - Troubleshooting
- https://github.com/pantor/frankx
    - Readme
    - example file

## Getting Started

1. 下載所有的檔案
2. 確保已經安裝所需套件

## 整體流程圖

![Untitled](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/bd0778fb-1134-4ccb-a2ac-afbc91adc060)


## LLM.py

- The existing tasks
    - catch
    - lookfor
    - give
    - putback
    - stack
    - unrelated
- The structure of guideline
    - The goal
        - example:
            
            ```
            Your task is to list a process based on 'User query' and Initial_grasps_state, using the following FUNCTION LIST to meet the user's needs.
            ```
            
    - The Function List
        - example
            
            ```
            FUNCTION LIST:
            - Name: {catch}
            - Description: Catching or grabbing the object.
            - REQUIREMENT: grasp_state == FALSE
            - FINAL_STATE: grasp_state == TRUE
            ```
            
    - The rule of listing a process
        - example
            
            ```
            Please adhere to the following steps when listing a process:
            
            1. Focus only on the content of the 'User query', and refrain from adding additional tasks afterward.
            2. Choose one or more functions from the FUNCTION LIST based on the 'User query'.
            3. If there are multiple possible functions, choose one of them.
            4. Review the `REQUIREMENT` and the `FINAL_STATE` of each chosen function from the FUNCTION LIST one by one.
            5. The `REQUIREMENT` of the first chosen function must match the `Initial_grasps_state`.
            If they don't match, choose other functions from the FUNCTION LIST to let them match.
            6. The `REQUIREMENT` of each chosen function must match the `FINAL_STATE` of its previous function.
            If they don't match, choose other function from the FUNCTION LIST to ensure that the `REQUIREMENT` of each chosen function match the `FINAL_STATE` of its previous function.
            7. Please think step by step.
            ```
            
    - Output format
        - example
            
            ```
            [
                {{
                    "`Name`": "the first chosen function",
                    "`REQUIREMENT`": "`The grasp state of the first chosen function`" (Must match `Initial_grasps_state`),
                    "`FINAL_STATE`": "`The grasp state of the first chosen function`"
                }},
                {{
                    "`Name`": "the second chosen function",
                    "`REQUIREMENT`": "`The grasp state of the second chosen function`" (Must match `FINAL_STATE` of its previous function),
                    "`FINAL_STATE`": "`The grasp state of the second chosen function`"
                }},
                {{
                    "`Name`": "the third chosen function",
                    "`REQUIREMENT`": "`The grasp state of the third chosen function`" (Must match `FINAL_STATE` of its previous function),
                    "`FINAL_STATE`": "`The grasp state of the third chosen function`"
                }},
                ...
            ]
            
            ```
            
    - Example
        - example
            
            ```
            #### START EXAMPLES
            'User query':
            Look for the object and catch the object finally give the object for me.
            
            `Initial_grasps_state`:
            "`grasp_state == FALSE`"
            
            ``
            [
                {{
                    "`Name`": "{lookfor}",
                    "`REQUIREMENT`": "`grasp_state == FALSE`",
                    "`FINAL_STATE`": "`grasp_state == FALSE`"
                }},
                {{
                    "`Name`": "{catch}",
                    "`REQUIREMENT`": "`grasp_state == FALSE`",
                    "`FINAL_STATE`": "`grasp_state == TRUE`"
                }},
                {{
                    "`Name`": "{give}",
                    "`REQUIREMENT`": "`grasp_state == TRUE`",
                    "`FINAL_STATE`": "`grasp_state == FALSE`"
                }}
            ]
            ``
            #### END EXAMPLES
            ```
            
    - Input
        - example
            
            ```
            ===Input===
            
            'User query':
            {input_text}
            
            `Initial_grasps_state`:
            {Initial_grasps_state}
            ```
            

- The word processing
    - Extract the content within square brackets.
        
        ```
        start_index = selected_tasks.find("[")
            end_index = selected_tasks.find("]")
        
            # Extract the content within square brackets.
            content = selected_tasks[start_index + 1:end_index].strip()
        
            # Match the value of 'name' using regular expressions.
            names = re.findall(r'"`Name`"\s*:\s*"([^"]+)"', content)
        ```
        

## RoboticArm.py

- catch
    - 限制條件
        - 只能抓取相機所拍攝到的範圍
        - 若相機有移動，會需要調整Offset
        - 0號Apriltag不會抓取
        - 目前只能做到roll的旋轉
    - 流程圖
        
        ![Untitled (1)](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/6f019208-d910-4d3b-ad11-1ef0c7b78d9a)

        
- lookfor
    - 限制條件
        - 只能偵測到相機所拍攝到的範圍
    - 流程圖
        
        ![Untitled (2)](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/d5f62ecc-bf1d-46e7-81e0-e4520d8f832c)

        
- give
    - 限制條件
        - 只會在限制區域進行給予
    - 流程圖
        
        ![Untitled (3)](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/0516470b-26b1-4855-9716-9532d3d3adfb)

        
- putback
    - 限制條件
        - 只會放置在指定區域
    - 流程圖
        
        ![Untitled (4)](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/58c4638e-3bc0-45bc-8d71-dab4d320aa96)

        
- stack
    - 限制條件
        - 只規劃在限制區域做堆疊
        - 若相機有移動，會需要調整Offset, letMesee
        - 只會堆疊在0號Apriltag上面
    - 流程圖
        
        ![Untitled (5)](https://github.com/YumingChennn/robot-arm-using-LLM/assets/126893165/e6436f51-d5a4-46ef-b0c8-ca4118d2afe4)

        

## 待改進項目

- LLM.py
    - 無法處理不合理的指令
        - 狀況：如果輸入不合理的語句時，會吐出錯誤的指令。
        - 解決方案：**ReAct prompting**
        - 參考連結：https://edge.aif.tw/application-react-prompting/

## 未來展望

- 語音輸入
    - 現狀：通過文字操控機器人
    - 未來：透過語音輸入，讓流程更加人性化。
- 物件夾取
    - 現狀：能夠通過Apriltag進行夾取
    - 未來：通過深度相機加上其他算法，進行物件夾取。

## Troubleshooting

- OSError: [libapriltag.so](http://libapriltag.so/): cannot open shared object file: No such file or directory
    - solution: [Link](https://stackoverflow.com/questions/28481900/oserror-cannot-open-shared-object-file-no-such-file-or-directory-even-though-f)
- AttributeError: 'NoneType' object has no attribute 'copy’
    - reason: The object is not within the field of view.
    - solution: put the object into the field of view.
- RuntimeError: Device disconnected. Failed to reconnect: No device connected5000.
    - reason:  Connection error.
    - solution: Replug the connection line.
- libfranka: Move command rejected: command not possible in the current mode ("User stopped")!
    - solution: Change the status of operation in the dashboard.
