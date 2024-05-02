import openai 
import json
import re

def askuserneed(grasp_state):

    # Set OpenAI API key
    openai.api_key = ''
    catch = 'Catch_the_object()'
    lookfor = 'Look_for_the_object()'
    give = 'Give_the_object_to_someone()'
    putback = 'Put_the_object_back()'
    stack = 'Stack_the_object()'
    unrelated = 'Task_unrelated_to_provided_options()'

    Initial_grasps_state = f'`grasp_state == {grasp_state}`'
    print(Initial_grasps_state)
    
    input_text = input("Please enter a piece of text:")

    def getSelectedTask(input_text, Initial_grasps_state, catch, lookfor, give, putback, stack, unrelated):

        while True:
            prompt = f"""Your task is to list a process based on 'User query' and `Initial_grasps_state`, using the following FUNCTION LIST to meet the user's needs.

Introduction of FUNCTION LIST
This FUNCTION LIST comprises six functions, each characterized by four attributes: `Name`, Description, 'REQUIREMENT', and 'FINAL_STATE'.
- `Name`: Name of the function.
- Description: Explanation of what the function accomplishes.
- `REQUIREMENT`: The grasp state matched to choose the function.
- `FINAL_STATE`: The grasp state after choosing the function.

FUNCTION LIST:
1.
    - `Name`: {catch}
    - Description: Catching or grabbing the object.
    - `REQUIREMENT`: `grasp_state == FALSE`
    - `FINAL_STATE`: `grasp_state == TRUE`

2.
    - `Name`: {lookfor}
    - Description: Rotating joints to look for the object on the table.
    - `REQUIREMENT`: `grasp_state == FALSE`
    - `FINAL_STATE`: `grasp_state == FALSE`

3.
    - `Name`: {give}
    - Description: Giving the object to someone or the user.
    - `REQUIREMENT`: `grasp_state == TRUE`
    - `FINAL_STATE`: `grasp_state == FALSE`

4.
    - `Name`: {putback}
    - Description: put the object back to the table.
    - `REQUIREMENT`: `grasp_state == TRUE`
    - `FINAL_STATE`: `grasp_state == FALSE`

5.
    - `Name`: {stack}
    - Description: Stacking the object in the workspace.
    - `REQUIREMENT`: `grasp_state == TRUE`
    - `FINAL_STATE`: `grasp_state == FALSE`

6.
    - `Name`: {unrelated}
    - Description: Choose this Function if 'User query' is not related to any other.
    - `REQUIREMENT`: Same as `FINAL_STATE` of the previous function.
    - `FINAL_STATE`: Same as `FINAL_STATE` of the previous function.
    

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

Ensure to output the result in the following JSON fromat, and provide your think process in each step above.
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

#### START EXAMPLES
'User query':
Look for the object and catch the object finally give the object for me.

`Initial_grasps_state`:
"`grasp_state == FALSE`"

```
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
```
#### END EXAMPLES

===Input===

'User query':
{input_text}

`Initial_grasps_state`:
{Initial_grasps_state}

""".strip()


            response = openai.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=300
            )
            task_choices = response.choices[0].text.strip()  # 将返回的文本分割为多个行
            print(task_choices)
            print(type(task_choices))
            if task_choices:
                return task_choices
            else:
                print("No valid choices found. Please try again.")
    
    selected_tasks = getSelectedTask(input_text, Initial_grasps_state, catch, lookfor, give, putback, stack, unrelated)

    start_index = selected_tasks.find("[")
    end_index = selected_tasks.find("]")

    # Extract the content within square brackets.
    content = selected_tasks[start_index + 1:end_index].strip()

    # Match the value of 'name' using regular expressions.
    names = re.findall(r'"`Name`"\s*:\s*"([^"]+)"', content)
    
    # Remove extra spaces and store in a list.
    names_list = [name.strip() for name in names]

    All_tasks = {
        'Catch_the_object()': 'catch',
        'Stack_the_object()': 'stack',
        'Give_the_object_to_someone()': 'give',
        'Put_the_object_back()': 'putback' , 
        'Look_for_the_object()': 'lookfor' ,
        'Task_unrelated_to_provided_options()': ''
    }
    
    tasks_mapping = []
    for task in names_list:
        tasks_mapping.append(All_tasks.get(task))
        print("selcted_tasked_mapping",tasks_mapping)

    with open("selected_task.json", "w") as f:
        json.dump(tasks_mapping, f)

    print("\nSelected tasks saved to selected_task.json")

