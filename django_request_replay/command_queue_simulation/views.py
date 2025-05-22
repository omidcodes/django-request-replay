from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

# In-memory store for testing replay
SIMULATED_STATE = {
    "command_queue": []
}


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'command': {'type': 'string', 'example': 'restart wifi'}
            },
            'required': ['command']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {'type': 'string'},
                'command': {'type': 'string'},
                'queue': {'type': 'array', 'items': {'type': 'string'}}
            }
        }
    }
)
@api_view(["POST"])
def enqueue_command(request):
    cmd = request.data.get("command")
    if not cmd:
        return Response({"error": "'command' is required."}, status=400)

    # Save in memory (volatile, simulating system state)
    SIMULATED_STATE["command_queue"].append(cmd)

    return Response({
        "status": "command added",
        "command": cmd,
        "queue": SIMULATED_STATE["command_queue"]
    })

@api_view(["DELETE"])
def clear_queue(request):
    SIMULATED_STATE["command_queue"] = []
    return Response({"status": "queue cleared"})

@api_view(["GET"])
def get_queue(request):
    return Response({"queue": SIMULATED_STATE["command_queue"]})