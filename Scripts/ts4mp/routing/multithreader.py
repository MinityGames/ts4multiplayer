import time
import gsi_handlers.routing_handlers
import elements
import sims4
from ts4mp.debug.log import ts4mp_log

import interactions.utils.routing
from element_utils import soft_sleep_forever

#ts4mp.reload Mods/ts4multiplayer/Scripts/ts4mp/routing/multithreader

gsi_handlers.routing_handlers.archiver._archive_enabled = True


def archive_plan(planner, path, ticks, time):
    ts4mp_log("Path plan time", "Plan Time, Ticks: {}, {}".format(time, ticks))


gsi_handlers.routing_handlers.archive_plan = archive_plan


class Timer():

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.t1 = time.time()

    def __exit__(self, *args):
        self.t2 = time.time()
        # if (self.t2 - self.t1) * 1000 > 50:
        ts4mp_log("Command path plan time: {}".format((self.t2 - self.t1) * 1000))


def generate_path(self, timeline):
    start_time = services.time_service().sim_now
    ticks = 0
    try:
        self.path.status = routing.Path.PLANSTATUS_PLANNING

        self.path.nodes.clear_route_data()
        if not self.route.goals:
            self.path.status = routing.Path.PLANSTATUS_FAILED
        else:
            for goal in self.route.goals:
                self.path.add_goal(goal)
            for origin in self.route.origins:
                self.path.add_start(origin)
            for (waypoint_group, waypoints) in enumerate(self.route.waypoints):
                for waypoint in waypoints:
                    waypoint.group = waypoint_group
                    self.path.add_waypoint(waypoint)
            self.sim.routing_component.on_plan_path(self.route.goals, True)
            if self.path.nodes.make_path() is True:
                plan_in_progress = True

                def is_planning_done():
                    nonlocal ticks, plan_in_progress
                    ticks += 1
                    plan_in_progress = self.path.nodes.plan_in_progress
                    return not plan_in_progress

                yield from element_utils.run_child(timeline, elements.BusyWaitElement(soft_sleep_forever(), is_planning_done))
                if plan_in_progress:
                    self.path.status = routing.Path.PLANSTATUS_FAILED
                else:
                    self.path.nodes.finalize(self._is_failure_route)
            else:
                self.path.status = routing.Path.PLANSTATUS_FAILED
            new_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
            new_route.path.copy(self.route.path)
            new_path = routing.Path(self.path.sim, new_route)
            new_path.status = self.path.status
            new_path._start_ids = self.path._start_ids
            new_path._goal_ids = self.path._goal_ids
            result_path = new_path
            if gsi_handlers.routing_handlers.archiver.enabled:
                gsi_handlers.routing_handlers.archive_plan(self.sim, self.path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
            num_nodes = len(new_path.nodes)
            if num_nodes > 0:
                start_index = 0
                current_index = 0
                for n in self.path.nodes:
                    if n.portal_object_id != 0:
                        portal_object = services.object_manager(services.current_zone_id()).get(n.portal_object_id)
                        if portal_object is not None and portal_object.split_path_on_portal(n.portal_id):
                            new_path.nodes.clip_nodes(start_index, current_index)
                            start_index = current_index + 1
                            if gsi_handlers.routing_handlers.archiver.enabled:
                                gsi_handlers.routing_handlers.archive_plan(self.sim, new_path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
                            if start_index < num_nodes:
                                new_route = routing.Route(self.route.origin, self.route.goals, additional_origins=self.route.origins, routing_context=self.route.context)
                                new_route.path.copy(self.route.path)
                                next_path = routing.Path(self.path.sim, new_route)
                                next_path.status = self.path.status
                                next_path._start_ids = self.path._start_ids
                                next_path._goal_ids = self.path._goal_ids
                                new_path.next_path = next_path
                                new_path.portal = portal_object
                                new_path.portal_id = n.portal_id
                                new_path = next_path
                            else:
                                new_path = None
                    current_index = current_index + 1
                if new_path is not None and start_index > 0:
                    end_index = current_index - 1
                    new_path.nodes.clip_nodes(start_index, end_index)
                    if gsi_handlers.routing_handlers.archiver.enabled:
                        gsi_handlers.routing_handlers.archive_plan(self.sim, new_path, ticks, (services.time_service().sim_now - start_time).in_real_world_seconds())
            self.route = result_path.route
            self.path = result_path
            self.sim.routing_component.on_plan_path(self.route.goals, False)
    except Exception:
        self.path.status = routing.Path.PLANSTATUS_FAILED
        self.sim.routing_component.on_plan_path(self.route.goals, False)
    if self.path.status == routing.Path.PLANSTATUS_PLANNING:
        self.path.set_status(routing.Path.PLANSTATUS_READY)
    else:
        self.path.set_status(routing.Path.PLANSTATUS_FAILED)

interactions.utils.routing.PlanRoute.generate_path = generate_path
from sims4.commands import CommandType
from _math import Vector3
from elements import GeneratorElement
from interactions.utils.routing import PlanRoute, FollowPath
from objects.components.types import ROUTING_COMPONENT
import element_utils
import routing
import services
import sims4.commands



@sims4.commands.Command('print_position', command_type=CommandType.Live)
def print_position(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output(str(services.get_active_sim().position))

@sims4.commands.Command('sf', command_type=CommandType.Live)
def routing_debug_follow( _connection=None):
    try:
        obj = services.get_active_sim()
        if obj is None:
            return False
        routing_component = obj.get_component(ROUTING_COMPONENT)
        if routing_component is None:
            return False
        pos = services.get_active_sim().position
        x = pos.x + 5
        y = pos.y 
        z = pos.z

        def _do_route_gen(timeline):
            try:
                with Timer("path planning"):
                    location = routing.Location(Vector3(x, y, z), routing_surface=obj.routing_surface)
                    goal = routing.Goal(location)
                    routing_context = obj.get_routing_context()
                    route = routing.Route(obj.routing_location, (goal,), routing_context=routing_context)
                    plan_primitive = PlanRoute(route, obj)
                    result = yield from element_utils.run_child(timeline, plan_primitive)
                    if not result:
                        return result
                    nodes = plan_primitive.path.nodes
                    if not nodes or not nodes.plan_success:
                        return False
                    follow_path_element = FollowPath(obj, plan_primitive.path)
                    result = yield from element_utils.run_child(timeline, follow_path_element)
                    if not result:
                        return result
                    return True
            except Exception as e:
                ts4mp_log("errors", str(e))
        timeline = services.time_service().sim_timeline
        timeline.schedule(GeneratorElement(_do_route_gen))
        return True
    except Exception as e:
        ts4mp_log("errors", str(e))
