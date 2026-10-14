
void __stdcall16far FUN_2000_e12b(void)

{
  byte bVar1;
  char cVar2;
  int *piVar3;
  int in_AX;
  int iVar4;
  uint uVar5;
  undefined2 uVar6;
  int in_BX;
  int unaff_BP;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  long lVar7;
  
  func_0x00032028(0x1000,1,0x51 - in_BX,in_AX + -1);
  iVar4 = FUN_3000_0458();
  *(int *)0x5c00 = iVar4;
  *(int *)0x5c02 = iVar4 >> 0xf;
  if (*(int *)0x5c00 != 0 || *(int *)0x5c02 != 0) goto LAB_2000_e387;
  FUN_3000_0772();
  FUN_3000_0d22();
  *(undefined2 *)0x5bce = 1;
  do {
    iVar4 = *(int *)0x5bce;
    bVar1 = *(byte *)(iVar4 + 0x5bd7);
    uVar5 = (uint)bVar1;
    *(uint *)0x5c0c = uVar5;
    if ((0x60 < bVar1) && (bVar1 < 0x7b)) {
      *(int *)(unaff_BP + -0x26) = uVar5 - 0x20;
      *(int *)(unaff_BP + -0x24) = -(uint)(uVar5 < 0x20);
      func_0x00032028(0x2e73,1,1,iVar4 + 0x5bd7);
    }
    *(int *)0x5bce = *(int *)0x5bce + 1;
  } while (*(int *)0x5bce < 0x3d);
  lVar7 = func_0x00032066(0x2e73,0,3,0x866);
  if (lVar7 != 0) {
    *(undefined2 *)0x5c06 = *(undefined2 *)0x3840;
    piVar3 = (int *)*(undefined4 *)(unaff_BP + 6);
    uVar6 = (undefined2)((ulong)piVar3 >> 0x10);
    if ((*piVar3 == 0 && ((int *)piVar3)[1] == 0) || ((*piVar3 == 1 && (((int *)piVar3)[1] == 0))))
    {
LAB_2000_e22d:
      *(undefined2 *)0x5c06 = 3;
    }
    else {
      piVar3 = (int *)*(undefined4 *)(unaff_BP + 6);
      if ((*piVar3 == 3) && (((int *)piVar3)[1] == 0)) goto LAB_2000_e22d;
      piVar3 = (int *)*(undefined4 *)(unaff_BP + 6);
      if ((*piVar3 == 4) && (((int *)piVar3)[1] == 0)) goto LAB_2000_e22d;
    }
    uVar6 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 6) >> 0x10);
    *(int *)0x5bd0 =
         *(int *)(*(int *)*(undefined4 *)(unaff_BP + 6) * 0x52 + 0x3528) + *(int *)0x383e;
    *(int *)0x5bd4 =
         *(int *)(*(int *)*(undefined2 *)(unaff_BP + 6) * 0x52 + 0x352a) + *(int *)0x3840;
    *(int *)0x5bd2 =
         *(int *)(*(int *)*(undefined2 *)(unaff_BP + 6) * 0x52 + 0x352c) - *(int *)0x383e;
    *(int *)0x5bd6 =
         *(int *)(*(int *)*(undefined2 *)(unaff_BP + 6) * 0x52 + 0x352e) - *(int *)0x5c06;
  }
  *(undefined2 *)(unaff_BP + -4) = 0x28;
  *(undefined2 *)(unaff_BP + -2) = 4;
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar4 = FUN_2000_8388(0x5bd8);
  if (((iVar4 != 0) && (*(int *)(unaff_BP + -0x12) == 1)) && (*(int *)(unaff_BP + -0x10) == 0)) {
    *(undefined1 *)0x5c09 = 1;
  }
  *(undefined2 *)(unaff_BP + -4) = 0x28;
  *(undefined2 *)(unaff_BP + -2) = 5;
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar4 = FUN_2000_8388(0x5bd8);
  if (iVar4 != 0) {
    *(undefined1 *)0x5c0a = *(undefined1 *)(unaff_BP + -0x12);
  }
  *(undefined2 *)(unaff_BP + -4) = 0x28;
  *(undefined2 *)(unaff_BP + -2) = 6;
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar4 = FUN_2000_8388(0x5bd8);
  if (iVar4 != 0) {
    *(undefined1 *)0x5c08 = *(undefined1 *)(unaff_BP + -0x12);
  }
  lVar7 = func_0x00032066(0x2e73,0,3,0x851);
  if ((lVar7 != 0) && (lVar7 = func_0x00032066(0x2e73,0,5,0x84c), lVar7 == 0)) {
    *(undefined1 *)0x5bcc = 1;
    *(undefined1 *)0x5c0a = 0x4b;
  }
LAB_2000_e387:
  func_0x00032028(0x2e73,1,0x51 - *(int *)0xa4,*(int *)0xa4 + 0xa5,0x54cc,0xd);
  func_0x00032028(0x2e73,1,0x51 - *(int *)0x52,*(int *)0x52 + 0x53,0x54cc,0xd);
  *(undefined2 *)0x5bce = 0;
  do {
    iVar4 = *(int *)0x5bce;
    cVar2 = *(char *)(iVar4 + 4);
    *(char *)(unaff_BP + iVar4 + -0x22) = cVar2;
    if ((*(char *)0x5c09 == '\x01') && (cVar2 != '\0')) {
      *(undefined1 *)(unaff_BP + iVar4 + -0x22) = 0xf;
    }
    *(int *)0x5bce = *(int *)0x5bce + 1;
  } while (*(int *)0x5bce < 0x10);
  FUN_3000_0458();
  FUN_3000_0de2(0x8ba,0x1c);
  FUN_3000_0d22();
  uVar6 = FUN_3000_7c9c();
  *(undefined2 *)0x5c04 = uVar6;
  return;
}

