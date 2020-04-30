import unittest
import json
from cloudsplaining.scan.policy_document import PolicyDocument


class TestPolicyDocument(unittest.TestCase):
    def test_policy_document_return_json(self):
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:PutImage"
                    ],
                    "Resource": "*"
                },
              {
                    "Sid": "AllowManageOwnAccessKeys",
                    "Effect": "Allow",
                    "Action": [
                        "iam:CreateAccessKey"
                    ],
                    "Resource": "arn:aws:iam::*:user/${aws:username}"
                }
            ]
        }
        policy_document = PolicyDocument(test_policy)
        result = policy_document.json
        # That function returns the Policy as JSON
        self.assertEqual(result, test_policy)

    def test_policy_document_return_statement_results(self):
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ssm:GetParameters",
                        "ecr:PutImage"
                    ],
                    "Resource": "*"
                },
              {
                    "Sid": "AllowManageOwnAccessKeys",
                    "Effect": "Allow",
                    "Action": [
                        "iam:CreateAccessKey"
                    ],
                    "Resource": "arn:aws:iam::*:user/${aws:username}"
                }
            ]
        }
        policy_document = PolicyDocument(test_policy)
        actions_missing_resource_constraints = []
        # Read only
        for statement in policy_document.statements:
            actions_missing_resource_constraints.extend(statement.missing_resource_constraints)
        self.assertEqual(actions_missing_resource_constraints, ['ecr:PutImage', 'ssm:GetParameters'])

        # Modify only
        modify_actions_missing_resource_constraints = []
        for statement in policy_document.statements:
            modify_actions_missing_resource_constraints.extend(statement.missing_resource_constraints_for_modify_actions())
        self.assertEqual(modify_actions_missing_resource_constraints, ['ecr:PutImage'])

        # Modify only but with include-action of ssm:GetParameters
        modify_actions_missing_resource_constraints = []
        for statement in policy_document.statements:
            modify_actions_missing_resource_constraints.extend(statement.missing_resource_constraints_for_modify_actions(["ssm:GetParameters"]))
        self.assertEqual(modify_actions_missing_resource_constraints, ['ecr:PutImage', 'ssm:GetParameters'])

    def test_policy_document_all_allowed_actions(self):
        """scan.policy_document.all_allowed_actions"""
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ssm:GetParameters",
                        "ecr:PutImage"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "AllowManageOwnAccessKeys",
                    "Effect": "Allow",
                    "Action": [
                        "iam:CreateAccessKey"
                    ],
                    "Resource": "arn:aws:iam::*:user/${aws:username}"
                }
            ]
        }
        policy_document = PolicyDocument(test_policy)
        result = policy_document.all_allowed_actions

        expected_result = [
            "ecr:PutImage",
            "ssm:GetParameters",
            "iam:CreateAccessKey"
        ]
        self.assertListEqual(result, expected_result)

    def test_allows_privilege_escalation(self):
        """scan.policy_document.allows_privilege_escalation"""
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole",
                        "lambda:CreateFunction",
                        "lambda:CreateEventSourceMapping",
                        "dynamodb:CreateTable",
                        "dynamodb:PutItem",
                    ],
                    "Resource": "*"
                }
            ]
        }
        policy_document = PolicyDocument(test_policy)
        results = policy_document.allows_privilege_escalation
        expected_result = [
            {
                "type": "PassExistingRoleToNewLambdaThenTriggerWithNewDynamo",
                "actions": [
                    "iam:passrole",
                    "lambda:createfunction",
                    "lambda:createeventsourcemapping",
                    "dynamodb:createtable",
                    "dynamodb:putitem"
                ]
            },
            {
                "type": "PassExistingRoleToNewLambdaThenTriggerWithExistingDynamo",
                "actions": [
                    "iam:passrole",
                    "lambda:createfunction",
                    "lambda:createeventsourcemapping"
                ]
            }
        ]
        self.assertListEqual(results, expected_result)

    def test_allows_specific_actions(self):
        test_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole",
                        "ssm:GetParameter",
                        "s3:GetObject",
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:GetParametersByPath",
                        "secretsmanager:GetSecretValue"
                    ],
                    "Resource": "*"
                }
            ]
        }
        policy_document = PolicyDocument(test_policy)
        results = policy_document.allows_specific_actions_without_constraints(["iam:PassRole"])
        self.assertListEqual(results, ["iam:PassRole"])
        # Input should be case insensitive, but give the pretty CamelCase action name result
        results = policy_document.allows_specific_actions_without_constraints(["iam:passrole"])
        self.assertListEqual(results, ["iam:PassRole"])

        # Verify that it will find the high priority read-only actions that we care about
        high_priority_read_only_actions = [
            "s3:GetObject",
            "ssm:GetParameter",
            "ssm:GetParameters",
            "ssm:GetParametersByPath",
            "secretsmanager:GetSecretValue"
        ]
        results = policy_document.allows_specific_actions_without_constraints(high_priority_read_only_actions)
        self.assertListEqual(results, high_priority_read_only_actions)
