import asyncio

# 异步队列
# 控制并发、限流、队列
class AsyncQueue:
    def __init__(self, maxsize=5):
        self.maxsize = maxsize
        self.semaphore = asyncio.Semaphore(value=maxsize)
        self.task = {}

    def is_run(self, task_id: int):
        # 判断任务是否在运行
        task = self.task.get(task_id)
        return not task.done() and task is not None

    def add_task(self, task_id:int,func):
        # 添加任务
        if self.is_run(task_id):
            return False
        task = asyncio.create_task(func)
        self.task[task_id] = task

        def callback(task: asyncio.Task):
            self.del_task(task_id, task)
        task.add_done_callback(callback)
        return True

    def del_task(self,task_id:int,task: asyncio.Task):
        self.task.pop(task_id)

    def __len__(self):
        return len(self.task)

    def reset_task_queue(self):
        self.task = {}


